from fastapi import FastAPI, Form, Request
from pydantic import BaseModel, ConfigDict, EmailStr, Field
app = FastAPI()


class UserCreate(BaseModel):
    name: str
    username : str
    email : EmailStr
    password : str
    
#  Response schema (NO password!)
class UserResponse(UserCreate):
    id: int
    username : str
    email : EmailStr
    password : str
    
    model_config = ConfigDict(from_attributes=True)
    


#  Register schema
class register(BaseModel):
    name: str
    username: str
    email: EmailStr
    password: str


#  Login schema
class LoginData(BaseModel):
    username: str
    password: str
    
"""class login(BaseModel):
    username:str
    passWord: str"""

#  OTP reset
class ResetPasswordOTP(BaseModel):
    email: EmailStr
    otp: str
    new_password: str
    
class EmailRequest(BaseModel):
    email: str