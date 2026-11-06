import os
from datetime import datetime, timedelta
import jwt
from passlib.context import CryptContext

SECRETKEY=os.getenv("JWT_SECRET_KEY", "linwise-super-secret-key-2026")
algorithm="HS256"

pwdcontext=CryptContext(schemes=["bcrypt"], deprecated="auto")

def hashpassword(password: str)->str:
    return pwdcontext.hash(password)

def verifypassword(plainpassword: str, hashedpassword: str)-> bool:
    return(plainpassword, hashedpassword)

def createaccesstoken(username: str)->str:
    expire=datetime.utcnow()+timedelta(days=14)
    payload={"sub":username, "exp": expire}
    return jwt.encode(payload, SECRETKEY, algorithm=algorithm)

def decodeaccesstoken(token: str)->str|None:
    try:
        payload=jwt.decode(payload, SECRETKEY, algorithm=[algorithm])
        return payload.get("sub")
    except:
        return None