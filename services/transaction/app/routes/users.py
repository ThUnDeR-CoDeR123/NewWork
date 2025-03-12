from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from app.models import Transaction, ReferralWallet, User
from app.database import get_db  
from app.schemas import transactionRequest,TokenData,TransactionFilter
from app.routes.utils import get_admin_user,get_normal_user,read_min_balance,assign_scheduler
from typing import Annotated
from fastapi.security import OAuth2PasswordBearer
from app.crud import addWithdrawal,readTransaction,createTransaction,getAdminWallet,resetAdminWallet,InterimToCryptoWallet,updateTransactionStatus
from starlette.responses import JSONResponse
import threading, datetime

# from app.routes.utils import router

user_router = APIRouter(prefix="/api/v1/transaction")


@user_router.post("/referral/withdrawal/add")
def request_withdrawal(withdrawal: transactionRequest, db : Annotated[Session , Depends(get_db) ]):
    if withdrawal.token_data is None:
        return JSONResponse(status_code=401, content={"message": "Unauthorized access"})
    token = withdrawal.token_data
    try:
        pending  = readTransaction(db,TransactionFilter(user_id=token.id,status=0,transaction_type=1,from_type=1))
        if len(pending) > 0:
            return JSONResponse(status_code=400, content={"error": "Transaction already in progress",
                                                          "message": "Please wait for the previous transaction to complete",
                                                          "details": "Transaction already in progress"})
        minBalance = read_min_balance()
        
        t= addWithdrawal(token.id, withdrawal.amount, db,minbalance=minBalance)
        

        return {"message": "Withdrawal request processed", "transaction_id": t.id}
    except Exception as e:
        return JSONResponse(status_code=400,content = {"message": str(e)})



@user_router.post("/transactions/view")
def view_transactions(filter: TransactionFilter , db : Annotated[Session , Depends(get_db) ]):
    if filter.token_data is None:
        return JSONResponse(status_code=401, content={"message": "Unauthorized access"})
    token = filter.token_data
    filter.user_id= token.id
   
    return readTransaction(db,filter)


@user_router.post("/transactions/crypto-deposit")
def crypto_deposit(data: transactionRequest , db : Annotated[Session , Depends(get_db) ]):
    token = data.token_data
    if token == None:
        return JSONResponse(status_code=401, content={"message": "Unauthorized access"}) 
    user_id = token.id
    print("Setting an admin wallet...")
    #chek for previous pending transactions
    pending = readTransaction(db,TransactionFilter(user_id=user_id,status=0,transaction_type=0,from_type=0))
    if len(pending) > 0:
        return JSONResponse(status_code=400, content={"error": "Transaction already in progress",
                                                      "message": "Please wait for the previous transaction to complete",
                                                      "details": "Transaction already in progress"})
    try:
        admin_wallet = getAdminWallet(db)  # Get admin wallet address
    except Exception as e:
        return JSONResponse(status_code=400, content={"error": "Admin wallet not found",
                                                      "message": "All the Wallets are Busy, Please try again later..",
                                                      "details": f"{str(e)}"})
    print("Initiating Pooling...")

    # Assigning the scheduler to update the wallet balance in the background
    try:
        t=createTransaction(admin_wallet.wallet_id,user_id,data.amount,db,status=0)
        if not t:
            raise Exception("Transaction not created, Please try again later")
        assign_scheduler(user_id,admin_wallet.wallet_id,t.id)
    except Exception as e:
        if t:
            updateTransactionStatus(db,t.id,data.amount,status=-1)
        print("pooling failed")
        print("Releasing assigned Admin wallet...")
        resetAdminWallet(db,admin_wallet.wallet_id)
        return JSONResponse(status_code=400, content={"error": "Scheduler not assigned",
                                                      "message": "All the Wallets are Busy, Please try again later..",
                                                      "details": f"{str(e)}"})
    
    return JSONResponse(status_code=200, content={"message": "Transaction is being processed",
                                                  "admin_wallet": admin_wallet.wallet_id,
                                                  "id": t.id})


@user_router.get("/check-status")
def check_status(transaction_id: int, db: Session = Depends(get_db)):
    t = db.query(Transaction).filter(Transaction.id == transaction_id).first()
    if t is None:
        return JSONResponse(status_code=404, content={"message": "Transaction not found"})
    return JSONResponse(status_code=200, content={"status": t.status})

# @user_router.post("/referral/add")
# def credit_user_wallet(token : Annotated[TokenData, Depends(get_normal_user)],credit: transactionRequest, db: Session = Depends(get_db)):
#     try:
#         t = addDeposit(db,token.id,credit.amount)
#         return {"message": "Transaction created successfully", "transaction_id": t.id}
#     except Exception as e:
#         return JSONResponse(status_code=400,content = {"error": str(e)})




