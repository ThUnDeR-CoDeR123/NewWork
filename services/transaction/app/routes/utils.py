from fastapi import APIRouter, HTTPException, Depends,status
from sqlalchemy.orm import Session
from app.models import Transaction, ReferralWallet, User
from app.database import get_db  # Assuming you have a DB session dependency
from pydantic import BaseModel
from app.crud import processTransaction,resetAdminWallet
import httpx
from app.schemas import TokenData
from fastapi.security import OAuth2PasswordBearer
import struct
from app.config import settings
from datetime import datetime, timedelta, timezone
import requests
import time
import threading
router = APIRouter(prefix="/api/v1/transaction")


oauth2_scheme = OAuth2PasswordBearer(tokenUrl=settings.auth_service_url + "/create_token")


async def getTokenDataFromAuthService(token:str = Depends(oauth2_scheme)): #the functionality is changed to return the tokendata
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{settings.auth_service_url}/verify_token",
            headers={"Authorization": f"Bearer {token}"}
        )
    if response.status_code != 200:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not validate credentials"
            )
    token_data = TokenData(id=response.json().get("id"),username=response.json().get("username"),flag=response.json().get("flag"),is_admin=response.json().get("is_admin"))
    if token_data.id is None:
            raise HTTPException(status_code=404, detail="User not found")
    return token_data


async def get_admin_user(token_data: TokenData ):
    if not token_data.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    return token_data


async def get_normal_user(token_data: TokenData ):
    if token_data is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unauthorized access"
        )
    if token_data.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admins are not allowed to access this resource"
        )
    return token_data



MIN_BALANCE_FILE = "min_balance.bin"

def write_min_balance(min_balance: float):
    with open(MIN_BALANCE_FILE, "wb") as f:
        f.write(struct.pack('f', min_balance))

def read_min_balance() -> float:
    try:
        with open(MIN_BALANCE_FILE, "rb") as f:
            return struct.unpack('f', f.read(4))[0]
    except FileNotFoundError:
        return 0.0
    

def check_for_transaction(user_id, start_time, admin_wallet_id, stop_event):
    """
    Checks for a valid crypto deposit transaction for up to 15 minutes.
    """
    print("Thread started...")
    polling_interval = 30  # Check every 30 seconds
    timeout = timedelta(minutes=5)
    with next(get_db()) as db:
        while not stop_event.is_set():
            try:
                response = requests.get(settings.apiurl)
                response.raise_for_status()
                data = response.json()
                print(data)
                if data["status"] == "1" and "result" in data:
                    print("status ok fond")
                    transactions = data["result"]
                    for txn in transactions:
                        txn_time = datetime.fromtimestamp(int(txn["timeStamp"]), tz=timezone.utc)  # Use timezone-aware UTC
                        txn_to = txn["to"].lower()  # Convert to lowercase for consistency
                        txn_hash = txn["hash"]
                        amount = float(txn.get("value")) / (10 ** int(txn["tokenDecimal"])) 

                        # Check if transaction is valid
                        if txn_time >= start_time and txn_to == admin_wallet_id.lower():
                            try:
                                #independent atomic functionality
                                print("processing transaction")
                                processTransaction(txn_hash,user_id,amount,admin_wallet_id)  # Process transaction
                            except Exception as e:
                                print(f"Error processing transaction: {str(e)}")
                                
                            finally:
                                print("Resetting admin wallet...")
                                resetAdminWallet(db,admin_wallet_id)

                                db.commit()
                                db.close()

                                print("Terminating thread...")  
                                stop_event.set()  # Stop scheduler
                                return

            except requests.RequestException as e:
                print(f"Error fetching transactions: {e}")

            # Check timeout condition
            if datetime.now(timezone.utc) - start_time >= timeout:
                print("Transaction not found within timeout...")
                print("resetting admin wallet...")
                resetAdminWallet(db,admin_wallet_id)

                db.commit()
                db.close()
                print("Terminating thread...")
                stop_event.set()  # Stop scheduler
                return

            time.sleep(polling_interval)  # Wait before next attempt

def assign_scheduler(user_id, admin_wallet_id):
    start_time = datetime.now(timezone.utc)  # Set start time with UTC awareness
    print("Thread starting... for Crypto-Deposit at start time : ",start_time)
    try:
        stop_event = threading.Event()  # Event to stop the scheduler
        thread = threading.Thread(target=check_for_transaction, args=(user_id, start_time, admin_wallet_id, stop_event))
        thread.start()
        print("thread started.. for Crypto-Deposit")
    except Exception as e:
        print(f"Error assigning scheduler: {str(e)}")

    return