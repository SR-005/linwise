import json
import pandas as pd
from typing import List,Dict
from PIL import Image
from pydantic import BaseModel, Field
from google import genai
from google.genai import types

from firebase import getattendence

def htmlparser(response: str) -> pd.DataFrame:
    htmlcontent=json.loads(response)["data"]
    df=pd.read_html(htmlcontent)[0]

    df.columns=df.columns.str.strip()
    df=df.drop(columns=['Attendance Percentage in Class','Duty Leave Hours'])

    df=df.rename(columns={
        df.columns[1]: "subjectname",
        df.columns[2]: "attended",
        df.columns[3]: "conducted",
        df.columns[4]: "percentage",
    })

    df=df.dropna(subset=["subjectname", "attended", "conducted"])
    df["attended"] = pd.to_numeric(df["attended"], errors="coerce")
    df["conducted"] = pd.to_numeric(df["conducted"], errors="coerce")

    df = df.drop(df[df["subjectname"] == "Total"].index)

    return df[["subjectname", "attended", "conducted"]]

def timetableparser(studentid: str, imagepath: str) -> Dict[str, List[str]]:
    attendence=getattendence(studentid)
    
    subjectdict={}
    for code, data in attendence.items():
        subjectdict[code]=data.get("subjectname",code)

    prompt=f"""
            You are an academic timetable analyzer.
            Examine this timetable table image and map each period slot (Monday to saturday) to the corresponding subject.

            CRITICAL MAPPING INSTRUCTIONS:
            - You must map each table cell to one of the exact subject slugs from this dictionary:
            {json.dumps(subjectdict, indent=2)}

            - If a subject or lab spans multiple consecutive periods/hours, repeat that subject's slug for every period it covers.
            - Return strictly the ordered list of periods for each day.
            """
if __name__=="__main__":
    timetableparser("P012CSOM23")