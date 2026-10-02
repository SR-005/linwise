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
            "subjectname": int(data.get("subjectname",subject))
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

    for dte,day in calendar.items():
        date=date.fromisoformat(date)
        if date>=fromdate and day.get("status")=="working":
            for period in day.get("periods",[]):
                subject=period.get("subject")
                if subject and subject!="free":
                    remaining[subject]=remaining.get(subject, 0)+1

def calculateattendence(studentid: str):
    _,studentdetails=getstudentdata(studentid)
    if not studentdetails.exists():
        print("Student details not Found!")
        return

    data=studentdetails.to_dict()
    attendence=data.get("attendence",{})
    calendar=data.get("studentcalender",{})

    today=date.today()
    tomorrow=today+timedelta(days=1)

    currentattendence=subjectreport(attendence,calendar,today)
    remaining=remaininghours(calendar,tomorrow)

    for subject,data in currentattendence.items():
        attended=data["attended"]
        conducted=data["conducted"]
        currentpercentage=(attended/conducted*100) if conducted>0 else 0.0

        hoursleft=remaininghours.get(subject,0)
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
        print(f"{subjectname:<30} | {currentpercentage:>6.2f}% | {hoursleft:>5} | {totalhours:>9} | {bunksleft:<12}")

    