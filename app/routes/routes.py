import os
import random
import re
from datetime import datetime, timedelta, timezone

import bcrypt
import yagmail
from dotenv import load_dotenv
from fastapi import Request, Depends, HTTPException, APIRouter
from fastapi.responses import RedirectResponse, HTMLResponse, JSONResponse
from sqlalchemy.orm import Session

from app.core.auth import (
    create_access_token,
    get_current_user,
    decode_access_token,
)
from app.db.database import engine, Base, get_db
from app.db.models import UsersDB, OTPCodes
from app.schemas.schemas import (
    register,
    ResetPasswordOTP,
    LoginData,
    EmailRequest,
)

load_dotenv()

router = APIRouter()

# create tables
Base.metadata.create_all(bind=engine)

pattern = r"^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*?&]).{8,}$"


# ── PAGE ROUTES ────────────────────────────────────────────────────────────

@router.get("/")
async def root():
    return RedirectResponse("/home")


@router.get("/home", response_class=HTMLResponse)
async def home_page(request: Request):
    response = request.app.state.templates.TemplateResponse("home.html", {"request": request})

    response.delete_cookie("access_token", path="/")

    return response


@router.get("/check-auth")
async def check_auth():
    return {"authenticated": True}


@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    return request.app.state.templates.TemplateResponse("login.html", {"request": request})


@router.get("/register", response_class=HTMLResponse)
async def register_page(request: Request):
    return request.app.state.templates.TemplateResponse("register.html", {"request": request})


@router.get("/request-otp", response_class=HTMLResponse)
async def request_otp_page(request: Request):
    return request.app.state.templates.TemplateResponse("request-otp.html", {"request": request})


@router.get("/reset-password", response_class=HTMLResponse)
async def reset_password_page(request: Request):
    return request.app.state.templates.TemplateResponse("reset-password.html", {"request": request})


@router.get("/dashboard", response_class=HTMLResponse)
async def dashboard_page(
        request: Request,
        user: dict = Depends(get_current_user),
        db: Session = Depends(get_db)
):
    username = user.get("sub")

    db_user = db.query(UsersDB).filter(
        (UsersDB.username == username) |
        (UsersDB.email == username)
    ).first()

    if not db_user:
        return RedirectResponse("/login")

    return request.app.state.templates.TemplateResponse("dashboard.html", {
        "request": request,
        "user": db_user
    })


# ── API ROUTES ─────────────────────────────────────────────────────────────


# ─────────────── REGISTER ───────────────

@router.post("/register")
async def register_user(user: register, db: Session = Depends(get_db)):
    existing_user = db.query(UsersDB).filter(
        (UsersDB.email == user.email) | (UsersDB.username == user.username)
    ).first()

    if existing_user is not None:
        raise HTTPException(status_code=400, detail="User already exists")

    if len(user.password) < 8 or not re.match(pattern, user.password):
        raise HTTPException(status_code=400, detail="Weak password")

    hashed = bcrypt.hashpw(user.password.encode(), bcrypt.gensalt()).decode()

    new_user = UsersDB(
        name=user.name,
        username=user.username,
        email=user.email,
        password=hashed
    )

    db.add(new_user)
    db.commit()

    return {"message": "Registration successful"}


# ─────────────── LOGIN ───────────────

@router.post("/login")
async def login_user(data: LoginData, db: Session = Depends(get_db)):
    user = db.query(UsersDB).filter(
        (UsersDB.username == data.username) | (UsersDB.email == data.username)
    ).first()

    if user is None:
        return JSONResponse(status_code=400, content={"detail": "User not found"})

    password_val = str(user.password)
    if not bcrypt.checkpw(data.password.encode(), password_val.encode()):
        return JSONResponse(status_code=400, content={"detail": "Invalid password"})

    token = create_access_token({"sub": data.username})

    response = JSONResponse({"message": "Login successful"})
    response.set_cookie(
        key="access_token",
        value=token,
        httponly=True,
        samesite="lax",
        secure=False  # ✅ FIX for localhost
    )

    return response


# ─────────────── REQUEST OTP ───────────────

def send_otp_email(to_email: str, otp: str):
    from_email = os.getenv("EMAIL_ADDRESS")
    from_password = os.getenv("EMAIL_PASSWORD")
    
    yag = yagmail.SMTP(from_email, from_password)
    yag.send(
        to=to_email,
        subject="Password Reset OTP",
        contents=f"Your OTP for password reset is: {otp}"
    )


@router.post("/request-otp")
async def request_otp(data: EmailRequest, db: Session = Depends(get_db)):
    user = db.query(UsersDB).filter(UsersDB.email == data.email).first()

    if user is None:
        return JSONResponse(status_code=400, content={"detail": "User not found"})

    otp = str(random.randint(100000, 999999))
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=5)

    db.query(OTPCodes).filter(OTPCodes.email == data.email).delete()

    db.add(OTPCodes(email=data.email, otp=otp, expires_at=expires_at))
    db.commit()

    try:
        send_otp_email(data.email, otp)
    except Exception as e:
        return JSONResponse(status_code=500, content={"detail": f"Failed to send email: {str(e)}"})

    return {"message": "OTP sent"}


# ─────────────── RESET PASSWORD ───────────────

@router.post("/reset-password")
def reset_password(data: ResetPasswordOTP, db: Session = Depends(get_db)):
    # 1. Find OTP record
    record = db.query(OTPCodes).filter(OTPCodes.email == data.email).first()
    if record is None:
        return JSONResponse(status_code=400, content={"detail": "OTP not found"})

    # 2. Validate OTP
    if str(record.otp) != str(data.otp):
        return JSONResponse(status_code=400, content={"detail": "Invalid OTP"})

    # 3. Check expiry
    expires_at_val = getattr(record, "expires_at")
    current_time = datetime.now(timezone.utc)
    is_expired = bool(expires_at_val is not None and current_time > expires_at_val)
    if is_expired:
        return JSONResponse(status_code=400, content={"detail": "OTP expired"})

    # 4. Find user
    user = db.query(UsersDB).filter(UsersDB.email == data.email).first()
    if user is None:
        return JSONResponse(status_code=400, content={"detail": "User not found"})

    # 5. Hash new password
    hashed = bcrypt.hashpw(data.new_password.encode(), bcrypt.gensalt()).decode()

    # Update via SQLAlchemy
    db.query(UsersDB).filter(UsersDB.email == data.email).update({"password": hashed})

    # 6. Delete OTP record
    db.query(OTPCodes).filter(OTPCodes.email == data.email).delete()
    db.commit()

    return {"message": "Password reset successful"}


# ─────────────── USERS ───────────────

@router.get("/users")
async def get_me(request: Request, db: Session = Depends(get_db)):
    token = request.cookies.get("access_token")

    if not token:
        return JSONResponse(status_code=401, content={"detail": "Not logged in"})

    payload = decode_access_token(token)
    username = payload.get("sub")

    user = db.query(UsersDB).filter(UsersDB.username == username).first()

    if user is None:
        return JSONResponse(status_code=404, content={"detail": "User not found"})

    now = datetime.now(timezone.utc)
    setattr(user, "last_login", now)
    db.commit()

    last_login_val = getattr(user, "last_login", None)

    return {
        "name": user.name,
        "username": user.username,
        "email": user.email,
        "last_login": str(last_login_val) if last_login_val is not None else None,
        "status": user.status if user.status is not None else "Active"
    }


# ─────────────── LOGOUT ───────────────

@router.get("/logout")
async def logout_user():
    response = RedirectResponse(url="/login", status_code=302)

    response.set_cookie(
        key="access_token",
        value="",
        max_age=0,
        expires=0,
        path="/",
    )

    return response


# Run app
if __name__ == "__main__":
    import uvicorn

    uvicorn.run(router, host="127.0.0.1", port=8000)