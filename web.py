import httpx
from bs4 import BeautifulSoup


BASEURL="https://aisat.linways.com"
LOGINURL=f"{BASEURL}/student/index.php?next=%2Fstudent%2Fstudent.php%3Fmenu%3Dhome"

username="P012CSOM23"
password="Sreeram2005"

def linwayssession(username: str, password: str) -> httpx.Client:
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

if __name__=="__main__":
    session=linwayssession(username,password)
    if session:
        dashboardres = session.get(f"{BASEURL}/student/student.php?menu=home")
        print(f"[+] Successfully fetched dashboard ({len(dashboardres.text)} bytes)")