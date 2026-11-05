import os
import json
from dotenv import load_dotenv
from typing import List, Optional, Tuple, Dict, Any

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.agents import create_agent
from langchain.tools import tool
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage, SystemMessage

import computations

load_dotenv()
studentid="P012CSOM23"

@tool
def markholidaytool(targetdate: str, reason: str = "Declared Holiday") -> dict:
    """Marks a specific calendar date (YYYY-MM-DD) as a holiday with a given reason."""
    success=computations.markholiday(studentid, targetdate, reason)
    return {"success": success, "date": targetdate, "status": "holiday", "reason": reason}

@tool
def unmarkholidaytool(targetdate: str) -> dict:
    """Reverts a holiday date (YYYY-MM-DD) back to a working day with default timetable periods."""
    success=computations.unmarkholiday(studentid, targetdate)
    return {"success": success, "date": targetdate, "status": "working"}

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
def simulatebunktool(targetdate: str, slots: list[int]=None) -> list:
    """Simulates the attendance percentage drop if classes are skipped on a given date."""
    return computations.simulatebunk(studentid, targetdate, slots)

tools=[markholidaytool, unmarkholidaytool, edittimetabletool, calculateattendancetool, getunmarkedtool, simulatebunktool]
toolmapping={t.name: t for t in tools}

SYSTEM_PROMPT = """You are Linwise AI, an intelligent KTU attendance companion.
- Your capabilities:
  1. Calculate attendance, remaining classes, and bunk buffers.
  2. Detect unposted Linways portal lag dates.
  3. Simulate bunk impacts on target dates and slots.
  4. Declare a date as a holiday (`mark_holiday_tool`) or revert a holiday back to a working day (`unmark_holiday_tool`).
  5. Update regular weekly timetable period slots (`edit_timetable_period_tool`).
- Always use the tools to make actual database updates or retrieve metrics. Keep responses crisp and direct.
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
        history.append(SystemMessage(content=SYSTEM_PROMPT))

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
                    content=tooloutput,
                    tool_call_id=toolcall["id"],
                    name=toolname
                )
            )

            #to check if the tool that is called required a widget in the chatbox
            if toolname=="getunmarkedtool" and rawdictdata:
                    widgetpayload={
                        "type": getunmarkedtool,
                        "unmarked": rawdictdata
                    }

        finalresponse=llmwithtools.invoke(history)      #second model call to generate NLP output to tool calling and its result etc
        history.append(finalresponse)
        replytext=extracttext(finalresponse.content)        #converting response content to string
    else:
        replytext=extracttext(response.content)

    return replytext, widgetpayload, history
            