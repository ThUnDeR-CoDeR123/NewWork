from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.schemas import TokenData
from app.database import get_db
from app.crud import getUserByEmail,getUserById,updateLastLogin
from fastapi.security import OAuth2PasswordBearer
from datetime import timedelta,datetime,timezone
from typing import Annotated, Union
from passlib.context import CryptContext
from jwt.exceptions import InvalidTokenError
from app.config import settings
import jwt


#create password context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
# set the token url
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/v1/auth/login")


# THIS FUNCTION WILL EITHER RETURN TRUE OR FALSE
def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password):
    return pwd_context.hash(password)


# A SINGLE FUNCTION WHICH WILL HANDEL TOKEN ENCODING FOR BOTH AUTHENTICATION AND FORGETPASSWORD
# flag = ["FORGET", "SIGNUP", "LOGIN"]
def create_access_token(data: dict, expires_delta: timedelta = timedelta(minutes=settings.access_token_expire_minutes), flag: str = "LOGIN"):
    #forget_token is optioal and if true it will say that this token is used for forgetpassword

    #COPY THE DATA TO BE ENCODED EG : {'sub': 5, 'email': 'example@example.com', 'is_admin': False} here sub contains user id
    to_encode = data.copy()
    
    #expiry timestamp is must for the token
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=15)


    #updated data : {'sub': 5, 'email': 'example@example.com', 'is_admin': False, 'exp': datetime.datetime(2024, 9, 8, 5, 6, 38, 851526, tzinfo=datetime.timezone.utc), 'forget_token': False}
    to_encode.update({"exp": expire,"flag": flag})
    
    print(to_encode)
    encoded_jwt = jwt.encode(to_encode, settings.secret_key, algorithm=settings.algorithm)
    

    return encoded_jwt




#A SINGLE FUNCTION TO HANDLE TOKEN DECODATION FOR BOTH AUTHENTICATION AND FORGET PASSWORD
def verify_token(token: str):
    # print(token)
    payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
    # print(payload)
        
    #THE TOKEN DATA SHOULD BE OF THIS TYPE : {'sub': 5, 'email': 'example@example.com', 'exp': datetime.datetime(2024, 9, 8, 5, 6, 38, 851526, tzinfo=datetime.timezone.utc), 'forget_token': False}

    if payload.get("sub") is None:
        raise credentials_exception
    token_data = TokenData(id=payload.get("sub"),username=payload.get("email"),flag=payload.get("flag"),is_admin=payload.get("is_admin"))


    return token_data



# FUNCTION TO GET THE USER DATA AND CHECK WHETHER USER EXISTS
def authenticate_user(username: str, password: str, db: Session):
    
    #THSI FUNCTION RETURNS A USER DATABASE MODEL or FALSE
    user=getUserByEmail(username,db)

    user.last_login = datetime.now(timezone.utc)
    if not user:
        return False
    
    if not verify_password(plain_password=password, hashed_password=user.password):
        return False
    return user


#THIS FUNCTION WILL ONLY BE USED AS A DEPENDENCY FOR ROUTES
#IT RETRIVES THE USED FROM THE SUPPLIED TOKEN
async def get_current_user(token: Annotated[str, Depends(oauth2_scheme)],db : Annotated[Session, Depends(get_db)]):
    #TRY VERIFYING THE TOKEN WHETHER IT IS VALID OR NOT
    try:
        token_data = verify_token(token=token)
    except InvalidTokenError:
        raise credentials_exception
    
    #GETTING THE USER FROM THE DATABASE
    user = getUserById(id=token_data.id,db=db)

    #HANDEL EXA=CEPTION
    if user is None:
        raise credentials_exception
    
    return user


