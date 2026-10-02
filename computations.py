import math
from typing import Dict, Any, List
from datetime import date, timedelta
import math
from firebase import getstudentdata

def calculator(subjectdata: Dict[str, Any], targetpercentage: float=75.0) -> Dict[str, Any]:
    attended=int(subjectdata.get("attended",0))
    conducted=int(subjectdata.get("conducted",0))
    subjectname=subjectdata.get("subjectname", "Unknown Subject")

    if conducted == 0:
        return {
            "name": subjectname,
            "percentage": 0.0,
            "status": "safe", 
            "safebunks": 0,
            "classneeded": 0
        }

    currentpercentage=round((attended/conducted)*100,2)
    if currentpercentage>=targetpercentage:             #i.e, you have more than target percentage
        safebunks=max(0, math.floor((100.0 * attended - targetpercentage * conducted) / targetpercentage))
        return {
            "name": subjectname,
            "percentage": currentpercentage,
            "status": "safe",
            "safebunks": safebunks,
            "classneeded": 0,
        }
    else:
        needed=math.ceil((targetpercentage * conducted -100.0 * attended) / (100.0 - targetpercentage))
        return {
            "name": subjectname,
            "percentage": currentpercentage,
            "status": "shortage",
            "safebunks": 0,
            "classneeded": max(1,needed)
        }


def recalculatecurrent(attendence: dict, calender: dict, today: date):
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

def attendencedetails(subjectdict: Dict[str, Dict[str, Any]], targetpercentage: float=75.0) -> Dict[str, Any]:
    details=[calculator(subject, targetpercentage) for subject in subjectdict.values()]
    return details