from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
import uvicorn
from pydantic import BaseModel
import httpx

import httpx

import json
import pandas as pd
from datetime import date
from typing import List, Optional


from firebase import saveattendence, getattendence
import computations
from parsers import attendenceparser, periodattendenceparser, timetableparser, calenderparser, buildcalendar, editcalendar, updateattendence

app=FastAPI(title="Linwise")
app.mount("/static", StaticFiles(directory="static"), name="static")

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



@app.get("/")
def dashboard():
    return FileResponse("static/home.html")

#returns calculates percentages, bunk limits etc
@app.get("/api/attendance")
def apiattendance():
    data=computations.calculateattendence(studentid)
    return{"studentid": studentid, "subjects": data}

@app.get("/api/getunmarked")
def apigetunmarked():
    return {"unmarked": computations.getunmarkedsummary(studentid)}

class AttendenceStatusRequest(BaseModel):
    date: str
    action: str

@app.post("/api/markunmarked")
def apimarkunmarked(req: AttendenceStatusRequest):
    newstatus="present" if req.action=="allpresent" else "absent"
    success=computations.markunmarked(studentid, req.date, newstatus)
    if not success:
        raise HTTPException(status_code=400, detail="Failed to reconcile selected date.")
    return {"success": True, "date": req.date, "attendance": newstatus}

class SimulationRequest(BaseModel):
    date: str
    slots: Optional[List[int]]=None

@app.post("/api/simulate")
def apisimulate(req: SimulationRequest):
    results=computations.simulatebunk(studentid, req.date, req.slots)
    return {
        "results": results
    }

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

@app.post("/api/setup/timetable")
def apisetuptimetable():
    try:
        result=initialtimetable(studentid)
        return{
            "success": True, "message": "Timetable parsed and registered successfully.", "data": result
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Timetable parsing failed: {str(e)}")

if __name__=="__main__":
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)