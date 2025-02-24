from fastapi.responses import JSONResponse
from fastapi import FastAPI, HTTPException, Request,APIRouter
import requests
from fastapi.middleware.cors import CORSMiddleware
import json
from app.config import settings
from app.routes.users import user_router
from app.routes.admin import admin_router
from app.crud import InterimToCryptoWallet,updateReferralWallet
from contextlib import asynccontextmanager
import threading
import time
import schedule
import requests
from sqlalchemy.orm import Session




def startSchedulerInBackground():
    schedulerThread = threading.Thread(target=runScheduler, daemon=True)       # Create the thread
    schedulerThread.start()   
    schedule.every(2).minutes.do(updateWallet)    # Schedule the task
    schedule.every(2).minutes.do(updateReferralWallet) 
def runScheduler():
    while True:
        print("Scheduler running...")
        schedule.run_pending()
        time.sleep(1)

def stop_scheduler():
    schedule.clear()
def updateWallet():
    print("Updating CryptoWallet...")
    InterimToCryptoWallet()
    
@asynccontextmanager
async def lifespan(app: FastAPI):
    startSchedulerInBackground()
    
    yield

    stop_scheduler()



app = FastAPI(lifespan=lifespan)

route = APIRouter(prefix="/api/v1/transaction")



app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Adjust this to only allow your specific domains
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@route.get("/health")
async def health():
    return {'status':"OK"}

app.include_router(user_router)
app.include_router(admin_router)
app.include_router(route)