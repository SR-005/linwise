import os
import json
from dotenv import load_dotenv
from typing import List, Optional, Tuple, Dict, Any
from pydantic import BaseModel, Field

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.agents import create_agent
from langchain.tools import tool
from langchain_core.tools import StructuredTool
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage, SystemMessage

from firebase import getstudentdata
import computations

load_dotenv()
studentid="P012CSOM23"

def getallsubjects(studentid):
    studentobj, studentdetails=getstudentdata(studentid)
    if not studentdetails.exists:
        return []

    studentdata=studentdetails.to_dict()
    subjects=studentdata.get("subjects", {})
    subjectlist=list(studentdata.get("subjects", {}).keys())

    cleanedlist=[]
    for subject in subjectlist:
        splitname=subject.split("_")
        cleanedsubject=[word for word in splitname if not any(char.isdigit() for char in word)]
        cleanedsubject=" ".join(cleanedsubject)
        cleanedsubject=cleanedsubject[:-1] 
        cleanedlist.append(cleanedsubject)

    return cleanedlist

@tool
def markholidaytool(targetdate: str, reason: str = "Declared Holiday") -> dict:
    """Marks a specific calendar date (YYYY-MM-DD) as a holiday with a given reason."""
    success=computations.markholiday(studentid, targetdate, reason)
    return {"success": success, "date": targetdate, "status": "holiday", "reason": reason}

@tool
def reverttoworkingdaytool(targetdate: str) -> dict:
    """Reverts any date (holiday, exam day, or overridden day) back to a regular working day with the default timetable periods."""
    success=computations.reverttoworkingday(studentid, targetdate)
    return {"success": success, "date": targetdate, "status": "working"}

@tool
def markexamtool(targetdate: str, usershorthand: str ,subjectslug: str, attendance: str = "notmarked") -> dict:
    """Marks a calendar date (YYYY-MM-DD) as an Exam Day across all 6 periods.
    Args:
        targetdate: Date in YYYY-MM-DD format.
        subjectslug: The official course title if matched.
        usershorthand: The exact raw shorthand, abbreviation, or course name typed by the user in chat.
        attendance: 'notmarked', 'present', or 'absent'.
    """

    enrolled=getallsubjects(studentid)
    chosensubject=subjectslug.lower()
    
    shorthandlist,match,matchletters=[],[],[]
    largestindex=0
    if chosensubject not in enrolled:
        print(f"chosen: {subjectslug}")
        for subject in enrolled:
            shorthand=""
            for word in subject.split():
                shorthand+=word[0]
            shorthandlist.append(shorthand)
    
        #print(f"Shorthands: {shorthandlist}")
    
        for letter in usershorthand:
            matchletters.append(letter)
    
        for shorthand in shorthandlist:
            count = 0
            for letter in shorthand:
                if letter[0] in matchletters:
                    print(f"{letter[0]} is in {matchletters}")
                    count+=1
            match.append(count)
    
        largest=max(match)
        print(f"matched: {largest}")
        largestindex=match.index(largest)
        chosensubject=enrolled[largestindex]

    success = computations.setexamday(studentid, targetdate, chosensubject, attendance)
    return {
        "success": success,
        "date": targetdate,
        "subject": chosensubject,
        "status": "exam",
    }

@tool
def edittimetabletool(dayname: str, periodnumber: int, newsubject: str) -> dict:
    """Changes a subject for a given weekday (monday-saturday) and period slot (1-6) in the weekly timetable."""
    success=computations.edittimetable(studentid, dayname, periodnumber, newsubject)
    return {"success": success, "day": dayname, "period": periodnumber, "new_subject": newsubject}

@tool
def calculateattendancetool() -> list:
    """Calculates cumulative 75% runway metrics and safe bunks for all subjects."""
    return computations.calculateattendence(studentid)

@tool
def getunmarkedtool() -> dict:
    """Fetches all dates with unposted portal periods that need student reconciliation."""
    return computations.getunmarkedsummary(studentid)

@tool
def markunmarkeddatetool(targetdate: str, status: str = "present") -> dict:
    """Marks all pending/unmarked periods on a regular working day (YYYY-MM-DD) as either 'present' or 'absent'.
    Use this when the user is reconciling regular attendance, resolving portal
    lag, or says 'mark <date> as present/absent'. DO NOT use this for exams.
    """
    cleanstatus=(
        "present"
        if status.lower() in ["present", "p", "attended"]
        else "absent"
    )
    success=computations.markunmarked(studentid, targetdate, cleanstatus)
    return {"success": success, "date": targetdate, "status": cleanstatus}

@tool
def simulatebunktool(targetdate: str, slots: list[int]=None) -> list:
    """Simulates the attendance percentage drop if classes are skipped on a given date."""
    return computations.simulatebunk(studentid, targetdate, slots)

tools=[markholidaytool, reverttoworkingdaytool, markexamtool, edittimetabletool, calculateattendancetool, getunmarkedtool, markunmarkeddatetool, simulatebunktool]
toolmapping={t.name: t for t in tools}

SYSTEM_PROMPT = """You are Linwise AI, an intelligent KTU attendance companion for college students.

Capabilities & Tools:
1. Attendance & Bunk Analysis:
   - Calculate cumulative attendance, 75% runway metrics, and safe bunk buffers (`calculateattendancetool`).
   - Simulate percentage drop if classes are missed on specific dates or slots (`simulatebunktool`).
   - List dates with portal lag or unposted attendance periods (`getunmarkedtool`).

2. Attendance Overrides & Reconciliation:
   - Reconcile regular unposted dates (`markunmarkeddatetool`). Call this when the student says "mark [date] as present/absent".
   - Declare a date as a holiday with a reason (`markholidaytool`).
   - Declare a date as an Exam Day where 1 subject takes all 6 periods (`markexamtool`). ONLY invoke this if the student explicitly mentions an exam or test.
   - Revert any modified day back to normal timetable periods (`reverttoworkingdaytool`).
   - Edit recurring weekly timetable period slots (`edittimetabletool`).

Strict Subject Matching Rules:
- When calling `markexamtool`, inspect the "Student's Enrolled Subjects this semester" list.
- For ANY user acronym or initialism (e.g., 'ISE', 'AI', 'CC', 'EHE'), find the enrolled course whose word initials match that acronym (e.g., 'ISE' matches 'industrial safety engineering', NOT anything outside the list).
- ALWAYS pass the EXACT full course title string from the enrolled subjects list as `subjectslug`.
- If the user says "mark Oct 16 as present", use `markunmarkeddatetool`. NEVER call `markexamtool` unless "exam", "test", or "series" is mentioned.
- Keep responses concise and factual.
"""

llm=ChatGoogleGenerativeAI(model="gemini-flash-lite-latest")    #creating llm
llmwithtools=llm.bind_tools(tools)              #binding tools with llm

def extracttext(content) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        textblocks=[]
        for block in content:
            if isinstance(block, dict) and "text" in block:
                textblocks.append(block["text"])
            elif isinstance(block, str):
                textblocks.append(block)
        return "".join(textblocks)
    return str(content)

def agent(usermessage: str, chathistory: List[Any]) -> Tuple[str, Optional[Dict[str, Any]], List[Any]]:
    history=list(chathistory)
    if not history:
        subjects=getallsubjects(studentid)
        print(f"\nMy Subjects: {subjects}\n")
        fullsystemprompt=SYSTEM_PROMPT + f"\n\nStudent's Enrolled Subjects this semester:\n{json.dumps(subjects)}"
        history.append(SystemMessage(content=fullsystemprompt))

    history.append(HumanMessage(content=usermessage))

    response=llmwithtools.invoke(history)
    history.append(response)

    widgetpayload: Optional[Dict[str, Any]] = None

    if response.tool_calls:
        for toolcall in response.tool_calls:
            toolname=toolcall["name"]
            toolargs=toolcall["args"]

            selectedtool=toolmapping[toolname]
            tooloutput=selectedtool.invoke(toolargs)

            if isinstance(tooloutput, (dict, list)):
                toolcontent=json.dumps(tooloutput)
                rawdictdata=tooloutput
            else:
                toolcontent=str(tooloutput)
                try:
                    rawdictdata=json.loads(tooloutput)
                except:
                    rawdictdata={}

            history.append(
                ToolMessage(
                    content=toolcontent,
                    tool_call_id=toolcall["id"],
                    name=toolname
                )
            )

            #to check if the tool that is called required a widget in the chatbox
            if toolname=="getunmarkedtool" and rawdictdata:
                    widgetpayload={
                        "type": "getunmarkedtool",
                        "unmarked": rawdictdata
                    }

        finalresponse=llmwithtools.invoke(history)      #second model call to generate NLP output to tool calling and its result etc
        history.append(finalresponse)
        replytext=extracttext(finalresponse.content)        #converting response content to string
    else:
        replytext=extracttext(response.content)

    return replytext, widgetpayload, history
            