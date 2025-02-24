from fastapi import APIRouter, FastAPI, HTTPException, Path, Depends, Body
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from typing import Optional, List
from app.routes.routes import router
from fastapi.middleware.cors import CORSMiddleware


app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)
