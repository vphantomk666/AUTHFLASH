from fastapi import FastAPI
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware

from app.routes.routes import router

app = FastAPI()

# ✅ MIDDLEWARE HERE
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://127.0.0.1:5500"],   # or your frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# templates
templates = Jinja2Templates(directory="templates")
app.state.templates = templates

# routes
app.include_router(router)