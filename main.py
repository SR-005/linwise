import httpx

import json
import pandas as pd
from datetime import date


from firebase import saveattendence, getattendence
from computations import calculateattendence
from parsers import attendenceparser, periodattendenceparser, timetableparser, calenderparser, buildcalendar, editcalendar, updateattendence

BASEURL="https://aisat.linways.com"
LOGINURL=f"{BASEURL}/student/index.php?next=%2Fstudent%2Fstudent.php%3Fmenu%3Dhome"

studentid="P012CSOM23"
password="Sreeram2005"

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
        print("Success!")
        return client
    else:
        print("Fail")
        return None

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

    

def timetable(studentid: str):
    timetabledict=timetableparser(studentid,r"media\timetable.jpeg")

def calendar(session, studentid: str, update: bool):
    semstart=calenderparser(studentid, r"media\calender.pdf", "B. Tech S3/S5/S7")

    #semstart="2026-07-01"
    today=date.today()
    today=today.strftime("%Y/%m/%d")
    semid="7"

    baseurl="https://aisat.linways.com/student/attendance/ajax_attendance_display.php"

    params={    
        "fromday": semstart,
        "today": today,
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

def main():
    session=linwayslogin(studentid,password)
    if session:
        print("Session is Active! Fetching Attendence...")

        #attendence(session, studentid)
        #timetable(studentid)
        calendar(session, studentid, True)
        #editcalendar(studentid)
        calculateattendence(studentid)
        

    else:
        print("Session is not active. Something Happend :(")
        
if __name__=="__main__":
    main()