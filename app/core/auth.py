from jose import JWTError, jwt
from datetime import datetime, timedelta
from fastapi import HTTPException, Request
import os

SECRET_KEY = os.getenv("SECRET_KEY", "mysecret123")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 10

def get_secret_key():
    # secret = os.getenv("SECRET_KEY")
    # if not secret:
    #     raise HTTPException(status_code=500, detail="Server misconfigured")
    # return secret
    return SECRET_KEY


#  Create token
def create_access_token(data: dict, expires_delta: timedelta = None):
    to_encode = data.copy()

    expire = datetime.utcnow() + (
        expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )

    to_encode.update({
        "exp": expire,
        "sub": data.get("sub")  # ensure subject exists
    })

    return jwt.encode(to_encode, get_secret_key(), algorithm=ALGORITHM)


#  Decode token (helper)
def decode_access_token(token: str):
    try:
        payload = jwt.decode(token, get_secret_key(), algorithms=[ALGORITHM])
        username = payload.get("sub")

        if username is None:
            raise HTTPException(status_code=401, detail="Invalid token")

        return payload

    except JWTError:
        raise HTTPException(status_code=401, detail="Token expired or invalid")


#  Get current user (COOKIE-BASED)
def get_current_user(request: Request):
    token = request.cookies.get("access_token")

    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")

    return decode_access_token(token)


