from app.schemas import UserCreate, UserUpdate,OTP,OTPdetails,forgetEmail,VerifyEmail,UserFilter
from app.models import User,CryptoWallet,ReferralWallet,ReferralCount,InterimWallet,Entitlement,UserEntitlement
from app.database import get_db
from fastapi import Depends,HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text
from passlib.context import CryptContext
import random
import string
from ..models import Base
from datetime import timedelta,datetime,timezone
from sqlalchemy import MetaData , text 
import hashlib


pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def getPasswordHash(password):
    return pwd_context.hash(password)


def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password):
    return pwd_context.hash(password)

def updatePassword(id: str,new_hashed_password: str, db: Session ):
    db_user = getUserById(id,db)
    db_user.password = new_hashed_password
    db.commit()
    db.refresh(db_user)
    return db_user

# FUNCTION TO GET THE USER DATA AND CHECK WHETHER USER EXISTS
def authenticate_user(username: str, password: str, db: Session):
    
    #THSI FUNCTION RETURNS A USER DATABASE MODEL or FALSE
    user=getUserByEmail(username,db)
    print("authenticating user")
    user.last_login = datetime.now(timezone.utc)
    if not user:
        return False
    
    if not verify_password(plain_password=password, hashed_password=user.password):
        return False
    return user

#--------------------------------------------------------------------USER DB OPERATIONS ----------------------------------------------------------------
#Create
def generate_referral_code(user_id: int) -> str:

    base_string = f"{user_id}"

    hash_object = hashlib.sha256(base_string.encode())

    hash_digest = hash_object.hexdigest()[:8]  
    
    random_string = ''.join(random.choices(string.ascii_uppercase + string.digits, k=4))
    
    referral_code = f"{hash_digest}{random_string}"
    
    return referral_code


def createUser(user: UserCreate, db: Session = Depends(get_db)):
    try:
         
            print(1)
            existing_user = db.query(User).filter(User.email == user.email).first()
            if existing_user:
                raise HTTPException(status_code=422, detail="Email already registered")
            # referrer_user = db.query(User).filter(User.referral_code == user.referral_code).first()
            # if not referrer_user:
            #     raise HTTPException(status_code=422, detail="Invalid referral code")
        
            db_user = User(
                email=user.email,
                password=getPasswordHash(user.password),  # Assuming you have a function to hash the password
                full_name=user.full_name,
                referral_code="100"
            )

            db.add(db_user)
            db.flush()
            referral_code = generate_referral_code(db_user.id)
            db_user.referral_code = referral_code

            # Create and associate the CryptoWallet for the new user
            crypto_wallet = CryptoWallet(user_id=db_user.id, balance=0.0)
            referral_wallet = ReferralWallet(user_id=db_user.id, balance=0.0)
            interim_wallet = InterimWallet(user_id=db_user.id, balance=0.0)

            # Add the wallets to the session
            db.add(crypto_wallet)
            # print(0/0)
            db.add(referral_wallet)

            db.add(interim_wallet)

            # Initialize the user count in the userCount table
            userCountInit(db, db_user.id)

            db.refresh(db_user)

            # otp=createOtp(forgetEmail(email=user.email),db)
            return db_user.id
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=503, detail=f"{str(e)}")

    
def userCountInit(db_session: Session, user_id: int):
    levels = []
    for level in range(1, 13):  # Levels 1 to 12
        levels.append(ReferralCount(user_id=user_id, level=level, count=0))
    
    # Add and commit new entries
    db_session.add_all(levels)
    db_session.commit()
    print(f"Added levels 1 to 12 for user_id {user_id}")

# def verifyEmail(data : VerifyEmail,db: Session = Depends(get_db)):
#     user = getUserById(data.email)

#     if not user.is_verified and validateOtp(OTP(data.otp), db):
#         user.is_verified = True
#         db.add(user)
#         db.commit()
#         return {"message": "Email verified successfully"}
#     else:
#         raise HTTPException(status_code=400, detail="Invalid verification code")

def generatetreeChild(db_session: Session, root_user_id: int, max_depth: int = 12):
    query = text("""
        WITH RECURSIVE referral_tree AS (
            SELECT 
                r.id AS referral_id,
                r.referrer_id,
                r.referred_user_id,
                1 AS depth
            FROM referrals r
            WHERE r.referrer_id = :root_user_id AND r.del_flag = FALSE

            UNION ALL

            SELECT 
                r.id AS referral_id,
                r.referrer_id,
                r.referred_user_id,
                rt.depth + 1 AS depth
            FROM referrals r
            INNER JOIN referral_tree rt ON r.referrer_id = rt.referred_user_id
            WHERE rt.depth < :max_depth AND r.del_flag = FALSE
        )
        SELECT * FROM referral_tree;
    """)

    result = db_session.execute(query, {"root_user_id": root_user_id, "max_depth": max_depth})

    # Use fetchall() to get all rows
    rows = result.fetchall()

    # Convert rows to dictionaries
    try:
        # For modern SQLAlchemy versions where rows behave like mappings
        return [dict(row) for row in rows]
    except TypeError:
        # For older SQLAlchemy versions where rows are not directly mappable
        return [
            {"referral_id": row[0], "referrer_id": row[1], "referred_user_id": row[2], "depth": row[3]}
            for row in rows
        ]




def get_level_counts(db: Session, user_id: int):
    
    return (
        db.query(ReferralCount.level, ReferralCount.count)
        .filter(ReferralCount.user_id == user_id)
        .all()
    )
#Read
def getUserById(user_id: int, db: Session = Depends(get_db)):
    db_user = db.query(User).filter(User.id == user_id, User.del_flag == False).first()
    if db_user is None:
        raise HTTPException(status_code=404, detail="User not found or has been marked as deleted")
    return db_user


def getAllUsers(db: Session = Depends(get_db), fil : UserFilter=None):
    
    query = (
        db.query(
            User.id,
            User.email,
            User.full_name,
            User.last_login,
            User.created_at,
            User.updated_at,
            User.wallet_id,
            User.is_verified,
            User.referral_code,
            User.transaction_id,
            CryptoWallet.balance.label("Crypto_balance"),
            ReferralWallet.balance.label("Referral_balance"),
            InterimWallet.balance.label("Interim_balance")
        )
        .join(CryptoWallet, User.id == CryptoWallet.user_id, isouter=True)
        .join(ReferralWallet, User.id == ReferralWallet.user_id, isouter=True)
        .join(InterimWallet, User.id == InterimWallet.user_id, isouter=True)
        .filter(User.del_flag == False)
    )
    if fil and fil.email is not None :
        print("Filtering users with", fil.email)
        query = query.filter(User.email.like(f"%{fil.email}%"))
    if fil and  fil.page is not None and fil.limit is not None:
        offset = (fil.page - 1) * fil.limit
        query = query.offset(offset).limit(fil.limit)

    
    users = query.all()
    
    
    return users

def getUserByEmail(email: str, db: Session ):
    db_user = db.query(User).filter(User.email == email, User.del_flag == False).first()
    if db_user is None:
        raise HTTPException(status_code=404, detail="User not found or has been marked as deleted")
    return db_user

def getUserEntitlements(user_id: int, db: Session = Depends(get_db)):
    db_user = db.query(User).filter(User.id == user_id).first()
    query = text("""select cost,label from entitlement where id in (select entitlement_id from user_entitlement where user_id =:user_id);""")

    result = db.execute(query, {"user_id": user_id})
    rows = result.fetchall()
    return [{"cost": row[0], "label":row[1]} for row in rows]

#Update
def updateUser(user_id : int,user: UserUpdate, db: Session = Depends(get_db)):
    
        db_user = db.query(User).filter(User.id == user_id).first()
        if db_user is None:
            raise HTTPException(status_code=404, detail="User not found")

        for key, value in user.model_dump(exclude_unset=True,exclude= {"token_data"}).items():
            setattr(db_user, key, value)
            print("Updated", key, value)
        db.commit()
        db.refresh(db_user)
        return db_user


def updateUserWalletid(user_id : int,wallet_id: str, db: Session = Depends(get_db)):
    
        db_user = db.query(User).filter(User.id == user_id).first()
        if db_user is None:
            raise HTTPException(status_code=404, detail="User not found")

        db_user.wallet_id = None if wallet_id.strip() == "" else wallet_id
        db.commit()
        db.refresh(db_user)
        return db_user

#Delete
def deleteUser( user_id: int, db: Session = Depends(get_db)):
    """
    Sets the del_flag of the user and related records to True instead of deleting them.

    Args:
        user_id (int): ID of the user to be marked as deleted.
        db (Session): SQLAlchemy session.

    Returns:
        User: The updated user object with del_flag set to True.
    """

    db_user = db.query(User).filter(User.id == user_id).first()
    
    if db_user is None:
        raise HTTPException(status_code=404, detail="User not found")

    db_user.del_flag = True

    for entitlement in db_user.entitlements:
        entitlement.del_flag = True

    if db_user.crypto_wallet:
        db_user.crypto_wallet.del_flag = True

    if db_user.referral_wallet:
        db_user.referral_wallet.del_flag = True

    for referral in db_user.referrer_users:
        referral.del_flag = True


    for referral in db_user.referred_users:
        referral.del_flag = True


    db.commit()


    return db_user


#truncate Table User
def truncateUsersTable(db: Session = Depends(get_db)):
    try:
        # Truncate the users table and reset identity (auto-increment)
        db.execute(text("TRUNCATE TABLE users RESTART IDENTITY CASCADE"))
        db.commit()
        return {"message": "User table truncated and indexes reset successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An error occurred while truncating the user table: {e}")
    
#function to drop users
def truncateUserTable(db : Session = Depends(get_db)):
    try:
        
        db.execute(text("DROP TABLE users cascade"))
        db.commit()
        return True
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An error occurred while truncating the user table: {e}")

def deleteAllTable(db: Session = Depends(get_db)):
   try:
        # Reflect the database schema to get all tables
        meta = MetaData()
        meta.reflect(bind=db.get_bind())  # Reflect the tables from the database

        # Drop all tables with cascade to handle dependencies
        for table in reversed(meta.sorted_tables):  # Drop in reverse dependency order
            db.execute(text(f"DROP TABLE IF EXISTS {table.name} CASCADE;"))

        db.commit()
        return {"message": "All tables dropped successfully"}
   except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"An error occurred while dropping the tables: {e}")

def updateLastLogin(user: User,db: Session):
    if not user:
        raise HTTPException(status_code=404, detail="User does not exists")
    user.last_login = datetime.now(timezone.utc)
    db.commit()
    db.refresh(user)
    return user

def updateVerified(id: int, db: Session):
    user = getUserById(id,db)
    user.is_verified =True
    db.commit()
    db.refresh(user)
    return user

def setForgetToken( email:str, db:Session , token: str ):
    # token_hash = get_password_hash(token)
    user = getUserByEmail(email, db)
    user.otp = token
    db.commit()
    db.refresh(user)

def checkForgetToken( id:int, db:Session , token: str ):
    # token_hash = get_password_hash(token)
    user = getUserById(id, db)
    otp = user.otp
    user.otp = None
    db.commit()
    db.refresh(user)
    return [otp,token]
    
# #----------------------------------------------------------------OTP DB OPERATIONS  ----------------------------------------------------------------

# #Here create otp will generate a token
# def createOtp(data : forgetEmail,db: Session = Depends(get_db)):
#     # print("Creating OTP")
#     user = getUserByEmail(data.email,db)
    
#     otp = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
#     user.otp = otp
#     db.commit()
#     db.refresh(user)
#     # print("createotp done")
#     # print(otp)
#     return OTPdetails(id=user.id,email=data.email,otp=otp)

# def validateOtp(data : OTP,db: Session = Depends(get_db)):
#     user = db.query(User).filter(User.otp == data.otp).first()
#     if not user:
#         raise HTTPException(status_code=400, detail="Invalid OTP")
#     user.otp = "NULL" 
#     db.commit()
#     return user.email