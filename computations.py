import math
from typing import Dict, Any, List
from datetime import date, timedelta
import math
from firebase import getstudentdata

def subjectreport(attendence: dict, calender: dict, today: date):
    effectiveattendence={}
    for subject,data in attendence.items():
        effectiveattendence[subject]={
            "attended": int(data.get("attended",0)) ,
            "conducted": int(data.get("conducted",0)),
            "subjectname": str(data.get("subjectname",subject))
        }

    for date,day, in calender.items():
        date=date.fromisoformat(date)
        if date<today and day.get("status")=="working":
            for period in day.get("periods", []):
                subject=period.get("subject")
                attendence=period.get("attendence")

                if subject in effectiveattendence and subject!="free":
                    if attendence=="present":
                        effectiveattendence[subject]["attended"]+=1
                        effectiveattendence[subject]["conducted"]+=1
                    elif attendence=="absent":
                        effectiveattendence[subject]["conducted"]+=1

    return effectiveattendence

def remaininghours(calendar: dict, fromdate: date) -> Dict[str, int]:
    remaining: Dict[str, int]={}

    for date,day in calendar.items():
        date=date.fromisoformat(date)
        if date>=fromdate and day.get("status")=="working":
            for period in day.get("periods",[]):
                subject=period.get("subject")
                if subject and subject!="free":
                    remaining[subject]=remaining.get(subject, 0)+1

    return remaining

def calculateattendence(studentid: str):
    _,studentdetails=getstudentdata(studentid)
    if not studentdetails.exists:
        print("Student details not Found!")
        return
    data=studentdetails.to_dict()
    attendence=data.get("subjects",{})
    calendar=data.get("studentcalender",{})
  
    today=date.today()
    tomorrow=today+timedelta(days=1)

    currentattendence=subjectreport(attendence,calendar,today)
    remaining=remaininghours(calendar,tomorrow)

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

def simulatebunk(studentid: str, targetdate: str):
    _,studentdetails=getstudentdata(studentid)
    if not studentdetails.exists():
        print("Student details not Found!")
        return

    data=studentdetails.to_dict()
    attendence=data.get("attendence",{})
    calendar=data.get("studentcalender",{})
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

    periodonday=Dict[str, int]={}
    for period in periods:
        subject=period.get("subject")
        if subject and subject != "free":
            periodonday[subject]=periodonday.get(subject, 0) + 1

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