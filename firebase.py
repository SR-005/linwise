import firebase_admin
from firebase_admin import credentials, firestore

import pandas as pd

credential=credentials.Certificate("firebasekey.json")
firebase_admin.initialize_app(credential)
db=firestore.client()

STUDENTID="P012CSOM23"

def getstudentdata(studentid: str):
    studentobj=db.collection("students").document(studentid)
    studentdetails=studentobj.get()
    return studentobj, studentdetails

def saveattendence(studentid: str, df: pd.DataFrame):
    df["code"]=df["subjectname"].str.replace(r'[^a-zA-Z0-9]', '_', regex=True).str.lower().str.strip('_')       #eliminates every special char
    records=df.set_index("code")[["subjectname", "attended", "conducted"]].to_dict(orient="index")   

    db.collection("students").document(studentid).set({"subjects": records}, merge=True)
    print("Attendence is saved to Firebase")

def getattendence(studentid: str) -> dict:
    record=db.collection("students").document(studentid).get()
    attendence=record.to_dict().get("subjects",{}) if record.exists else {}
    return attendence

def savetimetable(studentid: str, timetabledata: dict):
    cleanedtimetable={}
    for day,periods in timetabledata.items():
        cleanedday=day.lower().strip()
        cleanedtimetable[cleanedday]=periods

    timetableobj=db.collection("students").document(studentid)
    timetableobj.set({"timetable": cleanedtimetable}, merge=True)
    print("Time Table saved to Firebase")

def gettimetable(studentid: str) -> dict:
    record=db.collection("students").document(studentid).get()
    return record.to_dict().get("timetable",{}) if record.exists else {}

def savedates(studentid: str, calenderdata: dict):
    db.collection("students").document(studentid).set({"academicdates": calenderdata}, merge=True)
    print("Academic Dates- Start, End and Holidays are saves to Firebase")

def getdates(studentid: str) -> dict:
    dates=db.collection("students").document(studentid).get()
    if not dates.exists:
        return{}
    dates=dates.to_dict().get("academicdates", {})