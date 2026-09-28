import json
import pandas as pd
from typing import List,Dict
from PIL import Image
from pydantic import BaseModel, Field
from google import genai
from google.genai import types

import os
from dotenv import load_dotenv
load_dotenv()

from firebase import saveattendence, getattendence, savetimetable

def attendenceparser(studentid: str, response: str):
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

    df=df[["subjectname", "attended", "conducted"]]

    saveattendence(studentid,df)

class TimeTableModel(BaseModel):
    monday: List[str]=Field(description="Ordered list of subject slugs for Monday periods")
    tuesday: List[str]=Field(description="Ordered list of subject slugs for Tuesday periods")
    wednesday: List[str]=Field(description="Ordered list of subject slugs for Wednesday periods")
    thursday: List[str]=Field(description="Ordered list of subject slugs for Thursday periods")
    friday: List[str]=Field(description="Ordered list of subject slugs for Friday periods")
    saturday: List[str]=Field(description="Ordered list of subject slugs for Saturday periods")


def displaytimetable(schedule: Dict[str, List[str]]):
    print("\n" + "=" * 65)
    print(f"{'Day':<10} | {'P1':<8} {'P2':<8} {'P3':<8} {'P4':<8} {'P5':<8} {'P6':<8}")
    print("-" * 65)
    for day, periods in schedule.items():
        # Shorten slugs for clean terminal viewing
        short_names = [p.split("__")[0][:7] if p != "free" else "FREE" for p in periods]
        row = " ".join(f"{name:<8}" for name in short_names)
        print(f"{day.capitalize():<10} | {row}")
    print("=" * 65)

def edittimetable(timetable: Dict[str, List[str]], subjects: List[str]) -> Dict[str, List[str]]:
    while True:
        displaytimetable(timetable)
        print("\nOptions:")
        print("  [1] Confirm and Save to Firestore")
        print("  [2] Edit a single period")
        choice=input("Enter choice (1/2): ").strip()

        if choice=="1":
            return timetable
        
        if choice=="2":
            day=input("Enter the day: ").strip().lower()
            if day not in timetable:
                print("Invalid Day")
                continue

            period1=int(input("Enter the Period Number: ").strip())-1
            for i,j in enumerate(subjects,1):
                print(f"[{i}] {j}")
            period2=int(input("Select the subject number: ").strip())-1

            timetable[day][period1]=subjects[period2]
            print("Period Swapped!")

def timetableparser(studentid: str, imagepath: str):
    attendence=getattendence(studentid)
    
    subjectdict={}
    for code, data in attendence.items():
        subjectdict[code]=data.get("subjectname",code)

    subjects=list(subjectdict.keys())+["free"]
    
    prompt=f"""
            You are an expert academic timetable parser with high-precision spatial grid comprehension.
            Extract the weekly schedule for Monday through Saturday into the structured schema.

            VALID ENROLLED SUBJECT CATALOG:
            {json.dumps(subjectdict, indent=2)}

            INSTRUCTIONS:

            1. LEGEND & ABBREVIATION RESOLUTION:
            - Inspect the timetable grid and any legend/index rows present at the bottom.
            - Match abbreviations, course codes, and lab labels to the most appropriate slug from the catalog above.
            - Account for minor OCR or typographical variations across the sheet (for example, "CL LAB" vs "CD LAB" both refer to the Compiler Lab course code CSL411).
            - Any academic course, laboratory, seminar, or project block MUST be mapped to its corresponding catalog slug.

            2. WHEN TO USE "free":
            - Use the slug "free" ONLY for:
            a) Explicitly empty/blank cells.
            b) Non-academic blocks (e.g., "P&T" / Placement Training).
            - NEVER assign "free" to an academic lecture or laboratory slot.

            3. SPATIAL COLUMN ALIGNMENT:
            - Locate the header row indicating period numbers (Periods 1 through 6).
            - Trace vertical column borders up to the header to determine exact period positions.
            - Merged spans: When a cell horizontally spans multiple periods (e.g., Periods 1 to 3, or Periods 4 to 6), REPEAT that subject slug across all covered periods.
            - Single cells: Occupy exactly one period slot. Do not duplicate single cells into adjacent periods.

            Ensure exact chronological ordering from Period 1 to Period 6 for every day. Output strictly valid JSON matching the schema.
            """

    client=genai.Client()
    img=Image.open(imagepath)

    response=client.models.generate_content(
        model="gemini-3.1-flash-lite",
        contents=[img, prompt],
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=TimeTableModel,
            temperature=0.1,
        ),
    )
    
    timetable=json.loads(response.text)
    edittimetable(timetable,subjects)
    savetimetable(studentid,timetable)


'''if __name__=="__main__":
    timetableparser("P012CSOM23",r"media\timetable.jpeg")'''