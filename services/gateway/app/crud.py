from app.models import User
from fastapi import HTTPException
from sqlalchemy.orm import Session
from datetime import datetime, timezone

# THIS FILE MAINTAINS ALL DATABASE OPERATIONS 


def getUserByEmail(email: str, db: Session ):
    # print("searching for user by email")
    db_user = db.query(User).filter(User.email == email).first()
   
    if db_user is None:
        raise HTTPException(status_code=404, detail="User not found")
    
    return db_user

def setForgetToken( email:str, db:Session , token: str ):
    # token_hash = get_password_hash(token)
    user = getUserByEmail(email, db)
    user.otp = token
    db.commit()
    db.refresh(user)
def getUserById(id: int, db: Session ):
    db_user = db.query(User).filter(User.id == id).first()
    if db_user is None:
        raise HTTPException(status_code=404, detail="User does not exists")
    return db_user


def updatePassword(id: str,new_hashed_password: str, db: Session ):
    db_user = getUserById(id,db)
    db_user.password = new_hashed_password
    db.commit()
    db.refresh(db_user)
    return db_user

def updateLastLogin(user: User,db: Session):
    if not user:
        raise HTTPException(status_code=404, detail="User does not exists")
    user.last_login = datetime.now(timezone.utc)
    db.commit()
    db.refresh(user)
    return user