from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from app.models import Transaction, ReferralWallet, User
from app.database import get_db  
from app.schemas import transactionRequest,TokenData,TransactionFilter,setMinBalance,approveTransition
from app.routes.utils import get_admin_user,write_min_balance,read_min_balance
from typing import Annotated
from fastapi.security import OAuth2PasswordBearer
from app.crud import addWithdrawal,addDeposit,getUserById,getReferralwalletByUserId,readTransactionAdmin,readTransaction
# from app.routes.utils import 
from starlette.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError



admin_router = APIRouter(prefix="/api/v1/transaction")



@admin_router.patch("/admin/referral/approve")
def approve_transaction(
    data: approveTransition,  # Expect JSON in the body
    db: Session = Depends(get_db)
):
    
    if data.token_data is None:
        return JSONResponse(status_code=401, content={"message": "Unauthorized access"})
    if data.token_data.is_admin is False:
        return JSONResponse(status_code=403, content={"message": "Admin access required"})
    
    allowed_statuses = [-1, 0, 1]
    status = data.status

    # Check if status is valid
    if status not in allowed_statuses:
        return JSONResponse(status_code=404, content="Unknown status")

    try:
            # Fetch the transaction by ID
            transaction = db.query(Transaction).filter(Transaction.id == data.transaction_id).first()
            
            if not transaction:
                raise HTTPException(status_code=404, detail="Transaction not found")
            
            # Ensure transaction is pending
            if transaction.status != 0:
                raise HTTPException(status_code=400, detail="Transaction is either approved or rejected previously")

            # Update transaction status
            transaction.status = status
            print(transaction.status,status)
            wallet = getReferralwalletByUserId(transaction.user_id, db)

            if not wallet:
                raise HTTPException(status_code=400, detail="No wallet found for transaction")

            # Update wallet balance based on status and transaction type
            if status == 1:
                if transaction.transaction_type == 0:
                    wallet.balance += transaction.ammount
                elif transaction.transaction_type == 1:
                    wallet.balance -= transaction.ammount


            db.commit()
            db.refresh(wallet)
            db.refresh(transaction)
            print("db added successfully")

    except Exception as e:
        db.rollback()  # Roll back in case of any error
        raise HTTPException(status_code=500, detail=f"An error occurred during transaction processing, {str(e)}")



    # Map statuses to messages
    msg = {1: "approved", -1: "rejected"}

    # Return the response with a success message
    return {
        "message": f"Transaction {msg[status]} successfully",
        "transaction_id": transaction.id
    }

@admin_router.post("/admin/view")
def view_transactions(filter: TransactionFilter , db : Annotated[Session , Depends(get_db) ]):
    if filter.token_data is None:
        return JSONResponse(status_code=401, content={"message": "Unauthorized access"})
    if filter.token_data.is_admin is False:
        return JSONResponse(status_code=403, content={"message": "Admin access required"})
    return readTransactionAdmin(db,filter)

@admin_router.post("/admin/view/usertransactions")
def view_transactions(filter: TransactionFilter , db : Annotated[Session , Depends(get_db) ]):
    if filter.token_data is None:
        return JSONResponse(status_code=401, content={"message": "Unauthorized access"})
    if filter.token_data.is_admin is False:
        return JSONResponse(status_code=403, content={"message": "Admin access required"})
    return readTransaction(db,filter)


@admin_router.post("/admin/referral/setlimit")
async def set_min_balance(min_balance: setMinBalance):
    if min_balance.token_data is None:
        return JSONResponse(status_code=401, content={"message": "Unauthorized access"})
    if min_balance.token_data.is_admin is False:
        return JSONResponse(status_code=403, content={"message": "Admin access required"})
    if min_balance.balance < 0:
        raise HTTPException(status_code=400, detail="Minimum balance must be a positive number")
    
    write_min_balance(min_balance.balance)
    
    return {"message": "Minimum withdrawal balance set successfully", "min_balance": min_balance.balance}


@admin_router.get("/admin/referral/getlimit")
async def get_min_balance(token: TokenData):
    if token is None:
        return JSONResponse(status_code=401, content={"message": "Unauthorized access"})
    if token.is_admin is False:
        return JSONResponse(status_code=403, content={"message": "Admin access required"})
    min_balance = read_min_balance()
    
    return {"min_balance": min_balance}

