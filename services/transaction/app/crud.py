from sqlalchemy.orm import Session
from app.models import ReferralWallet, Transaction, User,CryptoWallet,AdminWallet,InterimWallet
from app.schemas import TransactionFilter
from fastapi import HTTPException
from app.database import get_db
from datetime import datetime,timezone,timedelta
from sqlalchemy import desc
import requests
from app.config import settings
from urllib.parse import urlencode
from sqlalchemy.orm import joinedload
from sqlalchemy import func


def getUserById(db: Session, user_id: int) -> User:
    
    user =  db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user

def addWithdrawal(user_id: int, amount: float, db: Session,minbalance: int):
   # Fetch the user first to get the wallet_id
    
    user = getUserById(db,user_id)

    if not user:
        raise HTTPException(status_code=404, detail="User  not found")
    if not user.wallet_id:
        raise HTTPException(status_code=404, detail="user Wallet is not set")
    
    if user.referral_wallet.balance - amount <minbalance:
        raise HTTPException(status_code=404, detail="You do not have sufficient balance to withdraw")


    #balance logic to be implementes
    transaction = Transaction(
        wallet_id=user.wallet_id,
        user_id=user_id,
        transaction_type=1,  # Debit
        ammount=amount,
        status=0,  # Pending
        from_type=1  # Referral type
    )
    
   
    db.add(transaction)
    db.commit()
    db.refresh(transaction)

    return transaction

def readTransaction(db:Session,filter:TransactionFilter,):
    query = db.query(Transaction)
    
    # Apply filters
    if filter.user_id:
        query = query.filter(Transaction.user_id == int(filter.user_id))
    if filter.status is not None:
        query = query.filter(Transaction.status == filter.status)
    if filter.from_date:
        query = query.filter(Transaction.created_at >= filter.from_date)
    if filter.to_date:
        query = query.filter(Transaction.created_at <= filter.to_date)
    if filter.transaction_type:
        query = query.filter(Transaction.transaction_type == filter.transaction_type)
    if filter.from_type:
        query = query.filter(Transaction.from_type == filter.from_type)
    
    # Pagination
    transactions = query.order_by(desc(Transaction.created_at)).offset((filter.page - 1) * filter.limit).limit(filter.limit).all()

    return [
    {
        "id": t.id,
        "wallet_id": t.wallet_id,
        "user_id": t.user_id,
        "transaction_type": t.transaction_type,
        "amount": t.ammount,
        "created_at": t.created_at + timedelta(hours=5, minutes=30),
        "status": t.status,
        "created_by": t.created_by,
        "meta": t.meta,
        "transaction_id": t.transaction_id,
        "from_type": t.from_type
    }
    for t in transactions
]

def readTransactionAdmin(db: Session, filter: TransactionFilter):
    query = db.query(Transaction).options(joinedload(Transaction.user))
    
    # Apply filters
    if filter.user_id:
        query = query.filter(Transaction.user_id == int(filter.user_id))
    if filter.status is not None:
        query = query.filter(Transaction.status == filter.status)
    if filter.from_date:
        query = query.filter(Transaction.created_at >= filter.from_date)
    if filter.to_date:
        query = query.filter(Transaction.created_at <= filter.to_date)
    if filter.transaction_type:
        query = query.filter(Transaction.transaction_type == filter.transaction_type)
    if filter.from_type:
        query = query.filter(Transaction.from_type == filter.from_type)
    
    # Pagination
    transactions = (
        query.order_by(desc(Transaction.created_at))
        .offset((filter.page - 1) * filter.limit)
        .limit(filter.limit)
        .all()
    )

    # Construct response
    return [
        {
            "id": t.id,
            "wallet_id": t.wallet_id,
            "user_id": t.user_id,
            "transaction_type": t.transaction_type,
            "ammount": t.ammount,
            "created_at": t.created_at + timedelta(hours=5, minutes=30),
            "status": t.status,
            "created_by": t.created_by,
            "meta": t.meta,
            "transaction_id": t.transaction_id,
            "from_type": t.from_type,
            "user": {
                "id": t.user.id if t.user else None,
                "email": t.user.email if t.user else None,
                "full_name": t.user.full_name if t.user else None,
                "wallet_id": t.user.wallet_id if t.user else None,
                "is_verified": t.user.is_verified if t.user else None,
                "created_at": t.user.created_at if t.user else None,
                "updated_at": t.user.updated_at if t.user else None,
            } if t.user else None,
        }
        for t in transactions
    ]

def addDeposit(db: Session,user_id: int, amt: float) -> Transaction:
    user = getUserById(db,user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User  not found")
    if not user.wallet_id:
        raise HTTPException(status_code=404, detail="user Wallet is not set")
    
    transaction = Transaction(
        wallet_id=user.wallet_id,
        user_id=user_id,
        transaction_type=0,  # Credit transaction
        ammount=amt,
        status=0,
        from_type=1  # Referral type
    )
    db.add(transaction)
    db.commit()
    db.refresh(transaction)
    
    return transaction


def findUserByWalletId(walletId: str, db: Session):
    # Perform a case-insensitive query
    user = db.query(User).filter(func.lower(User.wallet_id) == walletId.lower()).first()

    if user:
        print(walletId, user.wallet_id, user.transaction_id, user.email)
    return user
def getReferralwalletByUserId(id: int, db: Session):
    wallet= db.query(ReferralWallet).filter(ReferralWallet.user_id == id).first()
    if not wallet:
        raise HTTPException(status_code=404,content={"error": "InvalidReferralWallet"})
    return wallet


def createTransaction(walletId: str, userId: int, amount: float, db: Session,transactionId: str=None,status:int =1):
    """Create a transaction for Crypto wallet"""
    # Check if a transaction with the same transaction ID already exists
    existingTransaction=None
    if transactionId:
        existingTransaction = db.query(Transaction).filter(Transaction.transaction_id == transactionId).first()
    
    if existingTransaction:
        print(f"Transaction with ID {transactionId} already exists. Skipping creation.")
        return  # Exit the function if a duplicate is found
   
    # Create a new transaction if no duplicate is found
    newTransaction = Transaction(
        transaction_id=transactionId,  # Assign the provided transaction ID
        wallet_id=walletId,
        user_id=userId,
        transaction_type=0,  # Assuming 0 for credit
        ammount=round(amount, 2),
        created_at=datetime.now(timezone.utc),
        status=status,  # Assuming 1 for completed
        from_type=0  # Assuming 0 for crypto
    )
    db.add(newTransaction)
    db.commit()
    db.refresh(newTransaction)
    print(f"Transaction with ID {transactionId} created successfully.")
    return newTransaction

def updateTransactionStatus(db:Session,transaction_id:str, ammount:float=None,status:int=0):
    transaction = db.query(Transaction).filter(Transaction.id == transaction_id).first()
    if not transaction:
        raise HTTPException(status_code=404, detail="Transaction not found")
    transaction.status = status
    if ammount:
        transaction.ammount = ammount
    db.commit()
    db.refresh(transaction)
    return transaction


def updateOrCreateCryptoWallet(userId: int, amount: float, db: Session):
    cryptoWallet = db.query(CryptoWallet).filter(CryptoWallet.user_id == userId).first()
    if cryptoWallet:
        cryptoWallet.balance += amount
    else:
        cryptoWallet = CryptoWallet(
            user_id=userId,
            balance=amount,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        db.add(cryptoWallet)

def updateOrCreateInterimWallet(userId: int, amount: float, db: Session):
    interimWallet = db.query(InterimWallet).filter(InterimWallet.user_id == userId).first()
    if interimWallet:
        interimWallet.balance += amount
    else:
        interimWallet = InterimWallet(
            user_id=userId,
            balance=amount,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        db.add(interimWallet)
    return interimWallet



def updateOrCreateAdminWallet(admin_wallet_id: int, amount: float, db: Session):
    adminWallet = db.query(AdminWallet).filter(AdminWallet.wallet_id == admin_wallet_id).first()
    if not adminWallet:
        raise HTTPException(400,'AdminWallet not found')
    adminWallet.balance += amount
    return adminWallet




def getAdminWallet(db: Session):
    wallet = db.query(AdminWallet).filter(AdminWallet.status == 0).first()

    if not wallet:
        raise HTTPException(status_code=404,content={"error": "No Admin wallet found."})
    # Set the wallet as active
    wallet.status = 1
    db.commit()
    db.refresh(wallet)

    return wallet
def resetAdminWallet(db: Session, wallet_id: str):
    """
    Resets a specific admin wallet by setting its status back to inactive.
    
    :param db: Database session.
    :param wallet_id: The unique identifier of the admin wallet to reset.
    """
    wallet = db.query(AdminWallet).filter(AdminWallet.wallet_id == wallet_id).first()

    if not wallet:
        raise HTTPException(status_code=404, detail={"error": "AdminWalletNotFound"})

    # Reset the status of the specific wallet
    wallet.status = 0
    db.commit()
    db.refresh(wallet)
    print(f"Admin wallet {wallet_id} has been reset to inactive")
    return {"message": f"Admin wallet {wallet_id} has been reset to inactive"}

def updateReferralWallet():
    print("Updating referral wallets...")
    #This function updates referral wallets  based on the corrosponding balance in cryptowallet
    db = next(get_db())
    try:
        db.begin()  # Explicitly start a transaction
        cryptoWallets = db.query(CryptoWallet).all()

        for wallet in cryptoWallets:
            referralWallet = db.query(ReferralWallet).filter(ReferralWallet.user_id == wallet.user_id).first()

            if referralWallet:
                referralWallet.balance += wallet.balance*0.5 # add 50% of the balance in referral wallet
            else:
                referralWallet = ReferralWallet(
                    user_id=wallet.user_id,
                    balance=wallet.balance,
                    created_at=datetime.now(timezone.utc),
                    updated_at=datetime.now(timezone.utc)
                )
                db.add(referralWallet)


        db.commit()  # Commit transaction if all operations succeed
        print("Crypto wallets have been successfully transferred to referral wallets.")
    except Exception as e:
        db.rollback()
        print(f"Database error: {str(e)}")
    finally:
        db.close()





def InterimToCryptoWallet():
    print("scheduler called InterimToCryptoWallet...")
    with next(get_db()) as db:
        try:
            db.begin()  # Explicitly start a transaction
            interimWallets = db.query(InterimWallet).all()
            print(len(interimWallets))
            for wallet in interimWallets:
                print("Iteration ongoring...")
                cryptoWallet = db.query(CryptoWallet).filter(CryptoWallet.user_id == wallet.user_id).first()

                if cryptoWallet:
                    print("corrosponding user's cryptowllet found...")
                    cryptoWallet.balance += wallet.balance
                    print("Balance: " + str(cryptoWallet.balance), " updated ")
                    db.commit()
                    db.refresh(cryptoWallet)

                else:
                    print("corrosponding user's cryptowllet not found, creating one...")
                    cryptoWallet = CryptoWallet(
                        user_id=wallet.user_id,
                        balance=0.0,
                        created_at=datetime.now(timezone.utc),
                        updated_at=datetime.now(timezone.utc)
                    )
                    if not createTransaction(wallet.user_id, wallet.user_id, wallet.balance, db):
                        raise Exception("Transaction not created")
                    cryptoWallet.balance += wallet.balance
                    db.add(cryptoWallet)
                    db.commit()
                    db.refresh(cryptoWallet)
                    print("Balance: " + str(cryptoWallet.balance), " updated ")
                print("Refreshing DB...")
                db.refresh(cryptoWallet)

            db.commit()  # Commit transaction if all operations succeed
            print("Interim wallets have been successfully transferred to crypto wallets.")
        except Exception as e:
            db.rollback()  # Rollback to prevent partial updates
            print(f"Database error: {str(e)}")
        finally:
            db.close()  # Always close the session







def processApiResponse(data: dict):
    print("ProcessingApiResponse")
    with next(get_db()) as db:
        try:
            if data.get("status") and "result" in data:
                print("data recived successfully")
                transactions = data["result"]
                for tx in transactions:
                    print("processing transaction")
                    wallet_id = tx.get("from")
                    amount = float(tx.get("value")) / (10 ** int(tx["tokenDecimal"])) 
                    inddigi_coin = amount * (21.0/25.0)


                    user = findUserByWalletId(wallet_id, db)
                    if not user:
                        print("user not found", wallet_id)
                    else:
                        print("user found")
                    if user:
                        print(user.transaction_id,tx.get("hash"))
                    if (user and ( not user.transaction_id or user.transaction_id != tx.get("hash") )) :
                        if amount< 25 :
                            print(amount, inddigi_coin, "insufficient amount, skipping transaction...")
                            continue
            

                        print("updatation initiated")
                        # Create a new transaction entry
                        if createTransaction(wallet_id, user.id, inddigi_coin, db,transactionId=tx.get("hash")):

                            #update transaction_id in user table
                            updateTransactionId(user.id,db,tx.get("hash"))
                            # Update or create the user's crypto wallet
                            updateOrCreateCryptoWallet(user.id, inddigi_coin, db)
                            print("Transactions processed successfully.")

                            #update the referral heirarchy and credit the reward
                            call_calculate_and_credit(user.id,amount)
                db.commit()
            else:
                print("API call returned no data or success flag is False.")
        except Exception as e:
            print(f"An error occurred: {e}")
            db.rollback()











def processTransaction(txn_hsh: str, user_id:int, ammount: float,adimn_wallet_id:str,transaction_id:str):
    with next(get_db()) as db:
        try: 
            user = updateTransactionId(user_id,db,txn_hsh)
            # Update or create the user's interim wallet
            adminWallet = updateOrCreateAdminWallet(adimn_wallet_id, ammount, db)
            interimWallet = updateOrCreateInterimWallet(user_id, ammount, db)
            updateTransactionStatus(db,transaction_id,ammount,1)
            print("Transactions processed successfully.")
            print("Updating referral wallets of parent hierarchy...")
            giveCommission = call_calculate_and_credit(user_id,ammount)
            if not giveCommission["success"]:
                raise Exception(f"Error processing referral hierarchy {str(giveCommission['error'])}")
        except Exception as e:
            updateTransactionStatus(db,transaction_id,ammount,-1)
            print(f"An error occurred: {str(e)}")
            db.rollback()
            db.close()
            raise HTTPException(status_code=400, detail={"message": "Error processing transaction",
                                                            "error": f"{str(e)}"})
        # call_calculate_and_credit(user_id,ammount)
        finally:
            db.commit()
            db.refresh(user)
            db.refresh(adminWallet)
            db.refresh(interimWallet)
            db.close()













def call_calculate_and_credit(user_id: int, base_amount: float) -> dict:
    """
    Makes a GET request to the /referral/hierarchy/calculate-and-credit endpoint with parameters in the URL.

    :param user_id: The user ID for whom the referral hierarchy is being calculated and credited.
    :param base_amount: The base amount used for calculating referral rewards.
    :return: A dictionary containing the API response.
    """
    # Define the endpoint URL
    base_url = f"{settings.referral_service_url}/hierarchy/calculate-and-credit"

    # Construct the URL with query parameters
    query_params = urlencode({
        "user_id": user_id,
        "base_amount": base_amount
    })
    url = f"{base_url}?{query_params}"

    try:
        # Make the GET request with the parameters in the URL
        response = requests.get(url)

        # Check if the response status code indicates success
        if response.status_code == 200:
            return {
                "success": True,
                "data": response.json()
            }
        else:
            return {
                "success": False,
                "error": response.json(),
                "status_code": response.status_code
            }

    except requests.exceptions.RequestException as e:
        # Handle any request exceptions (e.g., connection errors)
        return {
            "success": False,
            "error": str(e)
        }
    









def updateTransactionId(user_id : int, db : Session, transaction_id : str):
    user = getUserById(db, user_id)
    user.transaction_id = transaction_id
    return user
