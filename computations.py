import math
from typing import Dict, Any, List

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


def attendencedetails(subjectdict: Dict[str, Dict[str, Any]], targetpercentage: float=75.0) -> Dict[str, Any]:
    details=[calculator(subject, targetpercentage) for subject in subjectdict.values()]
    return details