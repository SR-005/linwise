import math
from typing import Dict, Any, List, Optional
from datetime import date, timedelta, datetime
import math
import re
from firebase import getstudentdata
import parsers

lockeddate=date(2026, 10, 19)
tomorrowdate=lockeddate+timedelta(days=1)
studentid="P012CSOM23"

#for normalizing subject names by stripping unwanted 
def normalizesubjectnames(name:str) -> str:
    if not name:
        return ""
    cleaned=re.sub(r"[^a-zA-Z0-9]", "_", name.lower())
    return re.sub(r"_+", "_", cleaned).strip("_")

def markholiday(studentid: str, targetdate: str, reason: str="Declared Holiday") -> bool:
    studentobj, studentdetails = getstudentdata(studentid)
    if not studentdetails.exists:
        return False

    data=studentdetails.to_dict()
    calendar=data.get("studentcalendar", {})
    if targetdate not in calendar:
        return False

    calendar[targetdate]["status"]="holiday"        #resetng the parameters
    calendar[targetdate]["reason"]=reason
    calendar[targetdate]["periods"]=[]

    studentobj.update({f"studentcalendar.{targetdate}": calendar[targetdate]})  #updating in firebase
    return True

def reverttoworkingday(studentid: str, targetdate: str) -> bool:
    studentobj, studentdetails = getstudentdata(studentid)
    if not studentdetails.exists:
        return False

    data=studentdetails.to_dict()
    calendar=data.get("studentcalendar", {})
    timeetable=data.get("timetable", {})
    if targetdate not in calendar:
        return False

    formatteddate = datetime.strptime(targetdate, "%Y-%m-%d").date()
    dayname = formatteddate.strftime("%A").lower()
    if dayname=="sunday" or parsers.evensaturdays(formatteddate):
        return False

    periods=timeetable.get(dayname,[])
    reconstructedperiods=[]
    for index, subject in enumerate(periods,start=1):
        reconstructedperiods.append({
            "slot": index,
            "subject": subject if subject else "free",
            "attendance": "free" if (not subject or subject == "free") else "notmarked",
            "source": "linways"
        })

    calendar[targetdate]["day"]=dayname
    calendar[targetdate]["status"]="working"
    calendar[targetdate]["reason"]=""
    calendar[targetdate]["periods"]=reconstructedperiods

    studentobj.update({f"studentcalendar.{targetdate}": calendar[targetdate]})
    return True

def edittimetable(studentid: str, dayname: str, periodnumber: int, newsubject: str)->bool:
    studentobj,studentdetails=getstudentdata(studentid)
    if not studentdetails.exists:
        return False

    data=studentdetails.to_dict()
    timetable=data.get("timetable", {})
    day=dayname.lower().strip()

    if day not in timetable or not (1 <= periodnumber <= 6):
        return False

    timetable[day][periodnumber-1]=newsubject
    studentobj.update({"timetable": timetable})
    return True

#creates a list of unmarked dates and return it to 'markunmarked()'
def getunmarked(calender: dict, today: date) -> Dict[str, List[dict]]:
    unmarked={}
    sorteddates=sorted(calender.keys())

    for datestr in sorteddates:
        currentdate=date.fromisoformat(datestr)
        if currentdate>=today:
            break

        day=calender[datestr]
        if day.get("status") in ["working", "exam"]:
            pendingperiods=[
                period for period in day.get("periods",[])
                if period.get("subject") and period.get("subject")!="free" and period.get("attendance")=="notmarked"
            ]
            if pendingperiods:
                unmarked[datestr]=pendingperiods
    return unmarked

def getunmarkedsummary(studentid: str,) -> Dict[str, List[dict]]:
    _,studentdetails=getstudentdata(studentid)
    if not studentdetails.exists:
        return {}

    data=studentdetails.to_dict()
    calendar=data.get("studentcalendar",{})
    return getunmarked(calendar, lockeddate)  #date.today()

def markunmarked(studentid: str, targetdate: str, status: str)-> bool:
    studentobj,studentdetails=getstudentdata(studentid)
    if not studentdetails.exists:
        return False

    data=studentdetails.to_dict()
    calendar=data.get("studentcalendar",{})

    if targetdate not in calendar:
        return False

    periodlist=calendar[targetdate].get("periods",[])
    for period in periodlist:
        if period.get("subject")!="free" and period.get("attendance")=="notmarked":
            period["attendance"]=status
            period["source"]="useroverride"

    studentobj.update({f"studentcalendar.{targetdate}.periods": periodlist})
    return True

def setexamday(studentid: str, targetdate: str, subjectslug: str, attendance: str="notmarked"):
    print(subjectslug)

    studentobj,studentdetails=getstudentdata(studentid)
    if not studentdetails.exists:
        return {}

    studentdata=studentdetails.to_dict()
    timetable=studentdata.get("timetable", {})
    calendar=studentdata.get("studentcalendar",{})
    subjects=studentdata.get("subjects", {})

    if targetdate not in calendar:
        return False

    formatteddate=datetime.strptime(targetdate, "%Y-%m-%d").date()
    dayname=formatteddate.strftime("%A").lower()
    cleantitle = subjectslug.strip()
    attendancevalue=attendance.lower().strip() if attendance else "notmarked"
    
    examperiods=[
        {
        "slot": i+1,
        "subject": cleantitle,
        "attendance": attendancevalue,
        "source": "useroverride",
        }
        for i in range(6)
    ]

    calendar[targetdate]["day"]=dayname
    calendar[targetdate]["status"]="exam"
    calendar[targetdate]["reason"]=f"Exam: {cleantitle}"
    calendar[targetdate]["periods"]=examperiods

    studentobj.update({f"studentcalendar.{targetdate}": calendar[targetdate]})
    return True

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
        if currentdate<today and day.get("status") in ["working", "exam"]:
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
def remaininghours(calendar: dict, fromdate: date, subjectkeylist: List, enddate: Optional[date] = None,) -> Dict[str, int]:
    remaining={}

    for datestr,day in calendar.items():
        formatteddate=date.fromisoformat(datestr)

        if formatteddate < fromdate:
            continue
        if enddate and formatteddate > enddate:
            continue

        if formatteddate>=fromdate and day.get("status") in ["working", "exam"]:
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
    _,studentdetails=getstudentdata(studentid)
    if not studentdetails.exists:
        return {}
    
    data=studentdetails.to_dict()
    attendence=data.get("subjects",{})
    calendar=data.get("studentcalendar",{})
  
    today=date.today()
    tomorrow=today+timedelta(days=1)

    settings=getstudentsettings(studentid)
    attendancethreshold=settings["attendancethreshold"]/100.0
    enddate=(date.fromisoformat(settings["enddate"]) if settings["enddate"] else None)

    currentattendence=subjectreport(attendence,calendar,lockeddate)
    remaining=remaininghours(calendar,tomorrowdate, list(currentattendence.keys()), enddate)

    print("\n" + "=" * 88)
    print(f"{'SUBJECT':<30} | {'CURR %':<8} | {'LEFT':<5} | {'PROJ TOT':<9} | {'MAX BUNKS':<12}")
    print("-" * 88)

    report=[]
    for subject,data in currentattendence.items():
        attended=data["attended"]
        conducted=data["conducted"]
        currentpercentage=(attended/conducted*100) if conducted>0 else 0.0

        hoursleft=remaining.get(subject,0)
        totalhours=conducted+hoursleft
        if totalhours==0:
            continue

        minrequired=math.ceil(attendancethreshold*totalhours)
        maxpossibleattended=attended+hoursleft
        bunksleft=maxpossibleattended-minrequired

        report.append({
            "key": subject,
            "subjectname": data["subjectname"],
            "attended": attended,
            "conducted": conducted,
            "percentage": currentpercentage,
            "left": hoursleft,
            "totalhours": totalhours,
            "maxbunks": bunksleft 
        })
    return report

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
        return []

    periods=currentday.get("periods",[])
    currentattendence=subjectreport(attendence,calendar,lockeddate)

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


    #bunk simulation
    bunkresult=[]
    for subject,hours in periodonday.items():
        if subject in currentattendence:
            attended=currentattendence[subject]["attended"]
            conducted=currentattendence[subject]["conducted"]
            beforebunk=(attended/conducted*100) if conducted>0 else 0.0

            afterbunk=(attended/(conducted+hours))*100
            difference=afterbunk-beforebunk

            subjectname=currentattendence[subject]["subjectname"][:25]
            bunkresult.append({
                "subject": subjectname,
                "currentpercentage": beforebunk,
                "newpercentage": afterbunk,
                "drop": difference,
                "cuthours": hours,
                "below75": afterbunk<75.0,
            })
    return bunkresult

if __name__=="__main__":
    calculateattendence("P012CSOM23")
    #simulatebunk("P012CSOM23", "2026-10-05")