import math
from typing import Dict, Any, List
from datetime import date, timedelta
import math
import re
from firebase import getstudentdata

#for normalizing subject names by stripping unwanted 
def normalizesubjectnames(name:str) -> str:
    if not name:
        return
    cleaned=re.sub(r"[^a-zA-Z0-9]", "_", name.lower())
    return re.sub(r"_+", "_", cleaned).strip("_")

#creates a list of unmarked dates and return it to 'markunmarked()'
def unmarkedperiods(calender: dict, today: date) -> Dict[str, List[dict]]:
    unmarked={}
    sorteddates=sorted(calender.keys())

    for datestr in sorteddates:
        currentdate=date.fromisoformat(datestr)
        if currentdate>=today:
            break

        day=calender[datestr]
        if day.get("status")=="working":
            pendingperiods=[
                period for period in day.get("periods",[])
                if period.get("subject") and period.get("subject")!="free" and period.get("attendance")=="notmarked"
            ]
            if pendingperiods:
                unmarked[datestr]=pendingperiods
    return unmarked

#finds the unmarked dates and marks them (full day or specific periods)
def markunmarked(studentid: str) -> bool:
    studentobj,studentdetails=getstudentdata(studentid)
    if not studentdetails.exists:
        print("Student Record not Found!")
        return False

    studentdetails=studentdetails.to_dict()
    calendar=studentdetails.get("studentcalendar") or {}

    today=date.today()
    unmarked=unmarkedperiods(calendar, today)

    if not unmarked:
        print("All period Attendence are marked till date!")

    totalunmarked=sum(len(period) for period in unmarked.values())
    print(f"Detected {len(unmarked)} days found with {totalunmarked} number of periods")

    updates={}
    for datestr, pending in unmarked.items():
        day=calendar[datestr]
        dayname=day.get("day","").upper()
        periods=day.get("periods",[])

        print(f"==================================================")
        print(f" Date: {datestr} ({day})")
        print(f" Pending Hours: {len(pending)}")

        for period in pending:
            print(f"   • Period {period['slot']}: {period['subject']}")

        print(" [1] Present for ALL pending hours")
        print(" [2] Absent for ALL pending hours")
        print(" [3] Custom (Mark specific slots)")
        print(" [4] Skip this date for now")
        choice=input("Select an option [1/2/3/4]: ").strip().lower()

        if choice=="1":
            for period in periods:
                if period.get("subject")!="free" and period.get("attendance")=="notmarked":
                    period["attendance"]="present"
                    period["source"]="useroverride"
            updates[f"studentcalendar.{datestr}.periods"]=periods
            print("Attendence Updated as Present")

        elif choice=="2":
            for period in periods:
                if period.get("subject")!="free" and period.get("attendance")=="notmarked":
                    period["attendance"]="absent"
                    period["source"]="useroverride"
            updates[f"studentcalendar.{datestr}.periods"]=periods
            print("Attendence Updated as Absent")

        elif choice=="3":
            bunkinput=input("Enter the Period Number of the Periods you bunked (e.g. 2, 4): ").strip()
            bunkedperiod={int(input.strip()) for input in bunkinput.split(",") if input.strip().isdigit()}

            for period in periods:
                if period.get("subject")!="free" and period.get("attendance")=="notmarked":
                    if period.get("slot") in bunkedperiod:
                        period["attendance"]="absent"
                        period["source"]="useroverride"
                    else:
                        period["attendance"]="present"
                        period["source"]="useroverride"
            updates[f"studentcalendar.{datestr}.periods"]=periods
            print("Attendence Updated")

        else:
            print(f"[*] Skipped {datestr}.")
            continue
        
    if updates:
        studentobj.update(updates)
        print(f"\n[+] Successfully reconciled and saved {len(updates)} day(s) to Firestore!")
        return True
    return False

#calculates the total conducted and attended hours per subject by considering both marked and unmarked periods. returns to 'calculateattendence()'
def subjectreport(attendence: dict, calender: dict, today: date):
    effectiveattendence={}
    namelookup={}

    for subject,data in attendence.items():
        normalizedname=normalizesubjectnames(subject)
        effectiveattendence[normalizedname]={
            "attended": int(data.get("attended",0)) ,
            "conducted": int(data.get("conducted",0)),
            "subjectname": str(data.get("subjectname",subject)),
            "rawname": subject
        }
        namelookup[normalizedname]=normalizedname
        if "subjectname" in data:
            namelookup[normalizesubjectnames(data["subjectname"])]=normalizedname

    for datestr,day, in calender.items():
        currentdate=date.fromisoformat(datestr)
        if currentdate<today and day.get("status")=="working":
            for period in day.get("periods", []):
                subject=period.get("subject","")
                if not subject or subject=="free":
                    continue

                subjectname=normalizesubjectnames(subject)
                subjectkey=namelookup.get(subjectname)

                if not subjectkey:
                    for key in effectiveattendence.keys():
                        if key in subjectname or subjectname in key:
                            subjectkey=key
                            break
            
                if not subjectkey:
                    continue

                attendence=period.get("attendance")
                source=period.get("source")

                if source=="useroverride":
                    if attendence=="present":
                        effectiveattendence[subjectkey]["attended"]+=1
                        effectiveattendence[subjectkey]["conducted"]+=1
                    elif attendence=="absent":
                        effectiveattendence[subjectkey]["conducted"]+=1

    return effectiveattendence

#calculates how many hours will we get for per subject from tomorrow. returns to 'calculateattendence()'
def remaininghours(calendar: dict, fromdate: date, subjectkeylist: List) -> Dict[str, int]:
    remaining: Dict[str, int]={}

    for datestr,day in calendar.items():
        formatteddate=date.fromisoformat(datestr)
        if formatteddate>=fromdate and day.get("status")=="working":
            for period in day.get("periods",[]):
                subject=period.get("subject")
                if subject and subject=="free":
                    continue

                subjectname=normalizesubjectnames(subject)
                subjectkey=None

                for key in subjectkeylist:
                    if key==subjectname or key in subjectname or subjectname in key:
                        subjectkey=key
                        break

                if subjectkey:
                    remaining[subjectkey]=remaining.get(subjectkey, 0)+1

    return remaining

#calculates detailed attendence report like current %, classes left to bunk etc
def calculateattendence(studentid: str):
    markunmarked(studentid)
    #print("All attendence is Marked as Either absent or Present")

    _,studentdetails=getstudentdata(studentid)
    if not studentdetails.exists:
        print("Student details not Found!")
        return
    data=studentdetails.to_dict()
    attendence=data.get("subjects",{})
    calendar=data.get("studentcalendar",{})
  
    today=date.today()
    tomorrow=today+timedelta(days=1)

    currentattendence=subjectreport(attendence,calendar,today)
    remaining=remaininghours(calendar,tomorrow, list(currentattendence.keys()))

    print("\n" + "=" * 88)
    print(f"{'SUBJECT':<30} | {'CURR %':<8} | {'LEFT':<5} | {'PROJ TOT':<9} | {'MAX BUNKS':<12}")
    print("-" * 88)

    for subject,data in currentattendence.items():
        attended=data["attended"]
        conducted=data["conducted"]
        currentpercentage=(attended/conducted*100) if conducted>0 else 0.0

        hoursleft=remaining.get(subject,0)
        totalhours=conducted+hoursleft
        if totalhours==0:
            continue

        minrequired=math.ceil(0.75*totalhours)
        maxpossibleattended=attended+hoursleft
        bunksleft=maxpossibleattended-minrequired

        if bunksleft>=0:
            bunkdisplay=f"{bunksleft} hours"
        else:
            bunkdisplay=f"DEFICIT ({abs(bunksleft)})"

        subjectname=data["subjectname"][:28]
        print(f"{subjectname:<30} | {currentpercentage:>6.2f}% | {hoursleft:>5} | {totalhours:>9} | {bunkdisplay:<12}")

#simulates bunking a day and its effect on the attendence
def simulatebunk(studentid: str, targetdate: str, slots: List[int]=None):
    _,studentdetails=getstudentdata(studentid)
    if not studentdetails.exists:
        print("Student details not Found!")
        return

    data=studentdetails.to_dict()
    attendence=data.get("subjects",{})
    calendar=data.get("studentcalendar",{})
    today=date.today()

    if targetdate not in calendar:
        print(f"[-] Date {targetdate} not within calendar bounds.")
        return

    currentday=calendar[targetdate]
    if currentday.get("status") != "working":
        print(f"[-] {targetdate} is marked as a {currentday.get('status').upper()} ({currentday.get('reason')}). No classes scheduled.")
        return

    periods=currentday.get("periods",[])
    currentattendence=subjectreport(attendence,calendar,today)

    simulatedslots=set(slots) if slots else None

    periodonday: Dict[str, int]={}
    misseddetails=[]

    for period in periods:
        slotnumber=period.get("slot")
        subject=period.get("subject")
        if not subject or subject=="free":
            continue

        if simulatedslots is None or slotnumber in simulatedslots:
            normalizedsubject=normalizesubjectnames(subject)
            matchedkey=None
            for key in currentattendence.keys():
                if key==normalizedsubject or key in normalizedsubject or normalizedsubject in key:
                    matchedkey=key
                    break

            if matchedkey:
                periodonday[matchedkey]=periodonday.get(matchedkey, 0) + 1
                misseddetails.append((slotnumber, currentattendence[matchedkey]["subjectname"]))

    if not periodonday:
        print(f"No actionable subject hours found to simulate on {targetdate}.")
        return

    scopelabel=f"Slots {sorted(list(simulatedslots))}" if simulatedslots else "FULL DAY"
    print("\n" + "=" * 80)
    print(f" BUNK SIMULATION: {targetdate} ({currentday.get('day').upper()}) — {scopelabel}")
    print("=" * 80)

    for slotnum,subjectname in misseddetails:
        print(f"  • Hour {slotnum}: {subjectname}")
    print("-" * 80)    

    #bunk simulation
    for subject,hours in periodonday.items():
        if subject in currentattendence:
            attended=currentattendence[subject]["attended"]
            conducted=currentattendence[subject]["conducted"]
            beforebunk=(attended/conducted*100) if conducted>0 else 0.0

            afterbunk=(attended/(conducted+hours))*100
            difference=afterbunk-beforebunk

            warning=" [CRITICAL: Drops below 75%]" if afterbunk<75.0 else ""
            subjectname=currentattendence[subject]["subjectname"][:25]
            print(f"• {subjectname} : {beforebunk:.2f}% -> {afterbunk:.2f}% ({difference:+.2f}%) [Miss {hours} hr]{warning}")

if __name__=="__main__":
    calculateattendence("P012CSOM23")
    #simulatebunk("P012CSOM23", "2026-10-05")