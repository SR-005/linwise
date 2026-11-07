import os
from dotenv import load_dotenv
from datetime import datetime, timedelta
import jwt
import bcrypt
from passlib.context import CryptContext

load_dotenv()
SECRETKEY=os.getenv("JWTSECRETKEY")
algorithm="HS256"

pwdcontext=CryptContext(schemes=["bcrypt"], deprecated="auto")

def hashpassword(password: str)->str:
    pwdbytes=password.encode("utf-8")
    salt=bcrypt.gensalt()
    return bcrypt.hashpw(pwdbytes, salt).decode("utf-8")

def verifypassword(plainpassword: str, hashedpassword: str)-> bool:
    pwdbytes=plainpassword.encode("utf-8")
    return bcrypt.checkpw(pwdbytes, hashedpassword.encode("utf-8"))

def createaccesstoken(username: str)->str:
    expire=datetime.utcnow()+timedelta(days=14)
    payload={"sub":username, "exp": expire}
    return jwt.encode(payload, SECRETKEY, algorithm=algorithm)

def decodeaccesstoken(token) -> str | None:
  if not token:
    print("Token is empty or null")
    return None

  try:
    if isinstance(token, list):
      if len(token) > 1 and token[0].lower() == "bearer":
        token = token[1]
      elif len(token) > 0:
        token = token[-1]
      else:
        return None

    tokenstr=str(token).strip().strip('"').strip("'")
    if tokenstr.lower().startswith("bearer "):
      tokenstr=tokenstr[7:].strip()

    if not tokenstr or tokenstr in ("null", "undefined"):
      print("Token string is empty, null, or undefined")
      return None

    tokenbytes=tokenstr.encode("utf-8")
    payload=jwt.decode(token_bytes, str(SECRETKEY), algorithms=[algorithm])

    username=payload.get("sub")
    print(f"Successfully decoded token for user: {username}")
    return username

  except Exception as e:
    print(f"Decode Failed: {type(e).__name__} -> {e}")
    return None

  except Exception as e:
    print(f"Decode Failed: {type(e).__name__} -> {e}")
    return None