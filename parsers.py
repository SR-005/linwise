import json
import re
from datetime import datetime
import pandas as pd
from typing import List,Dict, Optional
from PIL import Image
from pydantic import BaseModel, Field
from google import genai
from google.genai import types
import pdfplumber


import os
from dotenv import load_dotenv
load_dotenv()

from firebase import getstudentdata, saveattendence, getattendence, savetimetable, savedates

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



class HolidayModel(BaseModel):
    semesterstart:str=Field(description="Commencement date of classes (YYYY-MM-DD)")
    semesterend:str=Field(description="Last instructional day / end of classes (YYYY-MM-DD)")
    holidays:List[str]=Field(description="List of declared holiday dates in YYYY-MM-DD format") 

def editcalender(studentid: str):
    studentobj,studentdetails=getstudentdata(studentid)

    if not studentdetails.exists:
        raise ValueError("No valid Student Record Found!")

    studentdetails=studentdetails.to_dict()
    calendar=studentdetails.get("academicdates", {})
    timetable=studentdetails.get("timetable", {})

    while True:
        print("\n" + "=" * 45)
        print("         SEMESTER CALENDAR MANAGER         ")
        print("=" * 45)
        print("1. View schedule for a specific date")
        print("2. Mark a date as Holiday / Leave")
        print("3. Reset date to default timetable")
        print("5. Exit")
        choice=input("Select an option (1-5): ").strip()

        if choice==1:
            date=input("Enter the Date(YYYY-MM-DD): ").strip()
            schedule=calendar.get(date)
            if not schedule:
                print("No Schedule for the specified date is found!")
            else:
                print(f"\n--- {date} ({schedule['day_of_week'].upper()}) ---")
                print(f"Status       : {schedule['status'].upper()}")
                print(f"Effective Day: {schedule.get('effective_day')}")
                print(f"Note         : {schedule.get('note')}")
                print(f"Periods      : {schedule.get('periods')}")

        elif choice==2:
            date=input("Enter the Date to be Marked Holiday(YYYY-MM-DD): ").strip()
            if date not in calendar:
                print("Date is incorrect, please check the input again!")
                continue

            reason=input("Enter the reason for the holiday: ").strip
            calendar[date]["status"]="holiday"
            calendar[date]["effective_day"]=None
            calendar[date]["periods"]=[]
            calendar[date]["note"]=reason

            studentobj.update({f"academicdates.{date}": calendar[date]})
            print("Holiday is successfully updated!")

        elif choice==3:
            date=input("Enter the Date to Reset(YYYY-MM-DD): ").strip()
            if date not in calendar:
                print("Date is incorrect, please check the input again!")
                continue

            dayname=calendar[date]["day_of_week"]
            calendar[date]["status"]="working" if dayname!="sunday" else "holdiay"
            calendar[date]["effective_day"] = dayname if dayname != "sunday" else None
            calendar[date]["periods"] = timetable.get(dayname, []) if dayname != "sunday" else []

            studentobj.update({f"academicdates.{date}": calendar[date]})
            print("Information for the day has been reset.")

        elif choice=="4":
            break

def pagefinder(calenderpath: str, targetterm: str) -> List[int]:
    contentpages=[]
    with pdfplumber.open(calenderpath) as pdf:
        for index, page in enumerate(pdf.pages):
            text=page.extract_text() or ""
            text=text.lower().replace("b.tech","b. tech")
            if targetterm.lower() in text:
                contentpages.append(index+1)

        if not contentpages:
            raise ValueError("No Pages with valid Information found :(")
        else:
            print(f"Page Numbers: {contentpages}")
            return contentpages

def dateparser(content: str) -> Optional[str]:
    match=re.search(r"\b(\d{2})-(\d{2})-(\d{4})\b", content)
    if match:
        d, m, y = match.groups()
        return f"{y}-{m}-{d}"
    return None

def calenderparser(studentid: str, calenderpath: str, targetterm: str) -> dict:
    extractedtext=[]
    targetpages=pagefinder(calenderpath, targetterm)

    with pdfplumber.open(calenderpath) as pdf:
        for pagenumber in targetpages:
            page=pdf.pages[pagenumber-1]
            tables=page.extract_tables()

            print(f"Table Content: {tables}")

            for table in tables:
                for row in table:
                    cleanedrow=[str(cell).replace("\n", " ").strip() if cell else "" for cell in row]
                    rowtext=" ".join(cleanedrow)

                    if "commencement of" in rowtext.lower() and "s3/s5/s7" in rowtext.lower():
                        for cell in reversed(cleanedrow):
                            result=dateparser(cell)
                            if result:
                                semstart=result
                                break

                    if "class ends" in rowtext.lower():
                        for cell in reversed(cleanedrow):
                            result=dateparser(cell)
                            if result:
                                semend=result
                                break

                    extractedtext.append("| " + " | ".join(cleanedrow) + " |")

        print(f"Start     : {semstart}")
        print(f"End       : {semend}")

        prompt = f"""
        Analyze the extracted calendar table rows from KTU B.Tech academic calendar.
        Semester runs from {semstart} to {semend}.

        Extract all festival holidays, public holidays, and days marked with non-working events occurring strictly between {semstart} and {semend}.
        Ensure every date is formatted as YYYY-MM-DD.

        CALENDAR ROWS:
        {chr(10).join(extractedtext)}
        """
            
    client=genai.Client()
    response=client.models.generate_content(
        model="gemini-3.1-flash-lite",
        contents=[prompt],
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=HolidayModel,
            temperature=0.0
    ))

    result=json.loads(response.text)
    print("\n--- Extracted Calendar ---")
    print(f"Start     : {semstart}")
    print(f"End       : {semend}")
    print(f"Holidays  : {len(result.get('holidays', []))} days detected")
    print(f"Sample    : {result.get('holidays')[:5]}...")

    calenderdict={
        "semesterstart": semstart,
        "semesterend": semend,
        "holidays": sorted(list(set(result.get("holidays",[]))))
    }

    savedates(studentid, calenderdict)

if __name__=="__main__":
    #timetableparser("P012CSOM23",r"media\timetable.jpeg")
    calenderparser("P012CSOM23", r"media\calender.pdf", "B. Tech S3/S5/S7")