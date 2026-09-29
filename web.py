import httpx
from bs4 import BeautifulSoup

import json
import pandas as pd

from firebase import saveattendence, getattendence
from computations import attendencedetails
from parsers import attendenceparser, timetableparser

BASEURL="https://aisat.linways.com"
LOGINURL=f"{BASEURL}/student/index.php?next=%2Fstudent%2Fstudent.php%3Fmenu%3Dhome"

username="P012CSOM23"
password="Sreeram2005"

#creating linways session using POST request
def linwayslogin(username: str, password: str) -> httpx.Client:

    #headers for http post request to linways 
    headers={
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
        "Referer": f"{BASEURL}/student/index.php",
        "Origin": BASEURL,
    }
    client=httpx.Client(headers=headers, follow_redirects=True, timeout=15.0)

    #student username and password for completing login
    payload = {
        "studentAccount": username,
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
def attendence(session, username: str):
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
    #df=attendenceparser(username,response.text)

    '''attendencereport=getattendence(username)
    result=attendencedetails(attendencereport, targetpercentage=75.0)
    for r in result:
        print(r)'''   

def timetable(username: str):
    timetabledict=timetableparser(username,r"media\timetable.jpeg")

def main():
    session=linwayslogin(username,password)
    if session:
        print("Session is Active! Fetching Attendence...")

        #attendence(session, username)
        timetable(username)

    else:
        print("Session is not active. Something Happend :(")
        
if __name__=="__main__":
    main()