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

tools=[calculateattendancetool, getunmarkedtool, simulatebunktool]
toolmapping={t.name: t for t in tools}

SYSTEM_PROMPT = """You are Linwise AI, an intelligent KTU attendance companion.
- Your goal is to help students track their attendance, manage their 75% runway, simulate bunks, and resolve unposted portal dates.
- Always use the provided tools to fetch accurate real-time numbers. Never guess attendance percentages or bunk buffers.
- Provide direct, concise, and helpful explanations without unnecessary gyaan.
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

            history.append(
                ToolMessage(
                    content=tooloutput,
                    toolcallid=toolcall["id"],
                    name=toolname
                )
            )

            #to check if the tool that is called required a widget in the chatbox
            if toolname=="getunmarkedtool":
                rawdata=json.loads(tooloutput)
                if rawdata:
                    widgetpayload={
                        "type": getunmarkedtool,
                        "unmarked": rawdata
                    }

        finalresponse=llmwithtools.invoke(history)      #second model call to generate NLP output to tool calling and its result etc
        history.append(finalresponse)
        replytext=extracttext(finalresponse.content)        #converting response content to string
    else:
        replytext=extracttext(response.content)

    return replytext, widgetpayload, history
            