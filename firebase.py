import firebase_admin
from firebase_admin import credentials, firestore

import pandas as pd

credential=credentials.Certificate("firebasekey.json")
firebase_admin.initialize_app(credential)
db=firestore.client()

STUDENTID="P012CSOM23"

def saveattendence(studentid: str, df: pd.DataFrame):
    df["code"]=df["subjectname"].str.replace(r'[^a-zA-Z0-9]', '_', regex=True).str.lower().str.strip('_')       #eliminates every special char
    records=df.set_index("code")[["subjectname", "attended", "conducted"]].to_dict(orient="index")   

    db.collection("students").document(studentid).set({"subjects": records})
    print("Data is saved to db")

def getattendence(studentid: str) -> dict:
    record=db.collection("students").document(studentid).get()
    attendence=record.to_dict().get("subjects",{}) if record.exists else {}
    return attendence