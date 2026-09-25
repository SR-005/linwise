import httpx
from bs4 import BeautifulSoup

import json
import pandas as pd

BASEURL="https://aisat.linways.com"
LOGINURL=f"{BASEURL}/student/index.php?next=%2Fstudent%2Fstudent.php%3Fmenu%3Dhome"

username="P012CSOM23"
password="Sreeram2005"

def linwayslogin(username: str, password: str) -> httpx.Client:
    headers={
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
        "Referer": f"{BASEURL}/student/index.php",
        "Origin": BASEURL,
    }
    client=httpx.Client(headers=headers, follow_redirects=True, timeout=15.0)

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

    return df[["subjectname", "attended", "conducted"]]

def main():
    session=linwayslogin(username,password)
    if session:
        subjectwiseurl=f"{BASEURL}/student/attendance/ajax/ajax_subjectwise_attendance.php?action=GET_REPORT"

        ajaxheaders={
            "X-Requested-With": "XMLHttpRequest",
            "Referer": f"{BASEURL}/student/student.php?menu=attendance",
            "Accept": "*/*"
        }

        response=session.get(subjectwiseurl,headers=ajaxheaders)
        print(f"Code: {response.status_code}")
        print(f"Type: {response.headers.get('content-type')}")
        #print(f"Sample: {response.text[:1000]}")

        df=htmlparser(response.text)
        print(df)

if __name__=="__main__":
    main()