from fastapi import FastAPI, HTTPException, Header
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
import uvicorn
from pydantic import BaseModel
import httpx
from firebase import db

import httpx

import json
import pandas as pd
from datetime import date
from typing import List, Optional, Dict, Any

import auth
from firebase import saveattendence, getattendence, getstudentdata
import computations
from parsers import attendenceparser, periodattendenceparser, timetableparser, calenderparser, buildcalendar, editcalendar, updateattendence
from agent import agent

app=FastAPI(title="Linwise")
app.mount("/static", StaticFiles(directory="static"), name="static")

chatsession: Dict[str, List[Any]]={}

BASEURL="https://aisat.linways.com"
LOGINURL=f"{BASEURL}/student/index.php?next=%2Fstudent%2Fstudent.php%3Fmenu%3Dhome"

studentid="P012CSOM23"
password="Sreeram2005"

lockeddate="2026/10/19"

#creating linways session using POST request
def linwayslogin(studentid: str, password: str) -> httpx.Client:
    #headers for http post request to linways 
    headers={
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
        "Referer": f"{BASEURL}/student/index.php",
        "Origin": BASEURL,
    }
    client=httpx.Client(headers=headers, follow_redirects=True, timeout=15.0)

    #student studentid and password for completing login
    payload = {
        "studentAccount": studentid,
        "studentPassword": password
    }

    response=client.post(LOGINURL,data=payload)      #submitting the POST Request
    print(response)


    if response.status_code==200:
        return client
    else:
        return None

def getcalendar(session, studentid: str, update: bool):
    semstart=calenderparser(studentid, r"media\calender.pdf", "B. Tech S3/S5/S7")

    #semstart="2026-07-01"
    today=date.today()
    today=today.strftime("%Y/%m/%d")
    semid="7"

    baseurl="https://aisat.linways.com/student/attendance/ajax_attendance_display.php"

    params={    
        "fromday": semstart,
        "today": lockeddate,
        "semID": semid
    }
    
    headers={
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Referer": "https://aisat.linways.com/student/attendance/between_two_dates.php",  # Keeps Linways CSRF/referer checks happy
        "X-Requested-With": "XMLHttpRequest"
    }

    response=session.get(baseurl, params=params, headers=headers)
    response.raise_for_status()

    history=periodattendenceparser(response.text)

    if update:
        updateattendence(studentid, history)
    else:
        buildcalendar(studentid, history)

#all-in-all attendence function
def attendence(session, studentid: str):
    subjectwiseurl=f"{BASEURL}/student/attendance/ajax/ajax_subjectwise_attendance.php?action=GET_REPORT"

    #header for POST Request to fetch attendence details
    ajaxheaders={
        "X-Requested-With": "XMLHttpRequest",
        "Referer": f"{BASEURL}/student/student.php?menu=attendance",
        "Accept": "*/*"
    }

    response=session.get(subjectwiseurl,headers=ajaxheaders)
    print(f"Response Code: {response.status_code}")

    #function which takes the html and parses to tables using pandas
    df=attendenceparser(studentid,response.text)

def initialtimetable(studentid: str):
    timetableparser(studentid, r"media/timetable.jpeg")

class RegisterRequest(BaseModel):
    username: str
    password: str

class LoginRequest(BaseModel):
    username: str
    password: str

class ConnectLinwaysRequest(BaseModel):
    studentid: str
    password: str

class AttendenceStatusRequest(BaseModel):
    date: str
    action: str

class TimetableEditRequest(BaseModel):
    day: str
    period: str
    subject: str

class ChatRequest(BaseModel):
    message: str
    sessionid: Optional[str] = "defaultuser"

class ChatResponse(BaseModel):
    text: str
    widget: Optional[dict]=None
    sessionid: str

#sending current token for verification via auth.decodeaccesstoken()
def getcurrentuser(authorization: str=Header(None)):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Unauthorized")

    parts=authorization.split()
    if len(parts)!=2 or parts[0].lower()!="bearer":
        raise HTTPException(status_code=401, detail="Invalid authorization header format")

    token=parts[1]
    username=auth.decodeaccesstoken(token)
    if not username:
        raise HTTPException(status_code=401, detail="Invalid or expired session")
    return username

@app.get("/login")
def login_page():
  return FileResponse("static/login.html")


@app.get("/signup")
def signup_page():
  return FileResponse("static/signup.html")


@app.get("/connect")
def connect_page():
  return FileResponse("static/connect.html")

@app.get("/")
def dashboard():
    return FileResponse("static/home.html")

#new user register endpoint
@app.post("/api/auth/register")
def apiregister(req: RegisterRequest):
    userdetails= db.collection("users").document(req.username.lower())
    if userdetails.get().exists:
        raise HTTPException(status_code=400, detail="Username already taken")

    userdetails.set({
        "username": req.username.lower(),
        "passwordhash": auth.hashpassword(req.password),
        "linwaysconnected": False,
        "studentid": None
    })

    token=auth.createaccesstoken(req.username.lower())
    return {
        "success": True,
        "token": token,
        "username": req.username.lower(),
        "linwaysconnected": False
    }

@app.post("/api/auth/login")
def apilogin(req: LoginRequest):
    userdetails=db.collection("users").document(req.username.lower()).get()
    if not userdetails.exists:
        raise HTTPException(status_code=400, detail="User not found")

    userdata=userdetails.to_dict()
    if not auth.verifypassword(req.password, userdata.get("passwordhash","")):
        raise HTTPException(status_code=400, detail="Incorrect password")

    token=auth.createaccesstoken(req.username.lower())
    return {
        "success": True,
        "token": token,
        "username": req.username.lower(),
        "linways_connected": userdata.get("linwaysconnected", False),
        "studentid": userdata.get("studentid")
    }

@app.post("/api/auth/connectlinways")
def apiconnectlinways(req: ConnectLinwaysRequest, authorization: str=Header(None)):
    username=getcurrentuser(authorization)

    session=linwayslogin(req.studentid, req.password)
    if not session:
        raise HTTPException(status_code=400, detail="Invalid Linways Student ID or Password")
    session.close()

    userdetails=db.collection("users").document(username)
    userdetails.update({
        "linwaysconnected": True,
        "studentid": req.studentid,
        "linwayspassword": req.password
    })

    return {
        "success": True,
        "message": "Linways account linked successfully!",
        "studentid": req.studentid
    }

@app.post("/api/auth/status")
def apistatus(authorization: str=Header(None)):
    username=getcurrentuser(authorization)
    userrecord=db.collection("users").document(username).get()
    if not userrecord.exists:
        raise HTTPException(status_code=404, detail="User not found")
    
    userdata=userrecord.to_dict()
    return {
        "username": username,
        "linways_connected": userdata.get("linways_connected", False),
        "studentid": userdata.get("studentid")
    }

#to fetch and display calendar 
@app.post("/api/calendar")
def apigetcalendar():
    _,studentdetails=getstudentdata(studentid)
    if not studentdetails.exists:
        raise HTTPException(status_code=404, detail="Student record not found.")

    studentdata=studentdetails.to_dict()
    calendar=studentdata.get("studentcalendar", {})
    return {"calendar": calendar}

@app.get("/api/timetable")
def apigettimetable():
    _,studentdetails=getstudentdata(studentid)
    if not studentdetails.exists:
        raise HTTPException(status_code=404, detail="Student record not found.")

    studentdata=studentdetails.to_dict()
    return {"timetable": studentdata.get("timetable", {})}

@app.post("/api/timtable/edit")
def apiedittimetable(req: TimetableEditRequest):
    success=computations.edittimetable(studentid, req.day, req.period, req.subject)
    if not success:
        raise HTTPException(status_code=400, detail="Failed to update timetable period.")
    return {"success": True, "day": req.day, "period": req.period, "subject": req.subject}


#to mark any unmarked attendence slots
@app.post("/api/markunmarked")
def apimarkunmarked(req: AttendenceStatusRequest):
    newstatus="present" if req.action=="allpresent" else "absent"
    success=computations.markunmarked(studentid, req.date, newstatus)
    if not success:
        raise HTTPException(status_code=400, detail="Failed to reconcile selected date.")
    return {"success": True, "date": req.date, "attendance": newstatus}

#to sync the attendence from linways to existing data in firebase
@app.post("/api/sync")
def apisync():
    session=linwayslogin(studentid, password)
    if not session:
        raise HTTPException(status_code=401, detail="Linways Login Failed.")
    
    try:
        #attendence(session,studentid)
        getcalendar(session, studentid, True)
        return {
            "success":True,
            "message":"Attendance records and calendar successfully synced with Linways.",
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Sync Error: {str(e)}")
    finally:
        session.close()


#AI Chatbot helper Models and POST Endpoints
@app.post("/chat",response_model=ChatResponse)
async def chatbot(req: ChatRequest):
    sessionid=req.sessionid or "defaultuser"
    history=chatsession.get(sessionid,[])

    try:
        responsetext, responsewidget, updatedhistory=agent(req.message, history)
        chatsession[sessionid]=updatedhistory
        return ChatResponse(
            text=responsetext,
            widget=responsewidget,
            sessionid=sessionid
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Chat processing failed: {str(e)}")


if __name__=="__main__":
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)