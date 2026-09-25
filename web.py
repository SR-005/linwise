import httpx
from bs4 import BeautifulSoup


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
        print(f"Sample: {response.text[:1000]}")


if __name__=="__main__":
    main()