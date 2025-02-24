from fastapi import Depends, HTTPException, status,Request
from sqlalchemy.orm import Session
from app.schemas import TokenData
from app.database import get_db
from app.crud import getUserByEmail,getUserById,updateLastLogin
from datetime import timedelta,datetime,timezone
from typing import Annotated, Union
from passlib.context import CryptContext
from jwt.exceptions import InvalidTokenError
from app.config import settings
import jwt
from starlette.responses import JSONResponse

#create password context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
# set the token url


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
def verify_token(request: Request) -> TokenData | None:
    """Extracts, validates, and verifies JWT from Authorization header.
       - Returns `None` if the Authorization header is missing.
       - Raises an HTTPException for invalid, expired, or tampered tokens.
    """

    # Extract Authorization header
    authorization: str = request.headers.get("Authorization")
    
    if not authorization:
        return None  # No token provided, return None (instead of raising exception)

    # Ensure "Bearer <token>" format
    token_parts = authorization.split(" ")
    if len(token_parts) != 2 or token_parts[0].lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token format. Expected 'Bearer <token>'."
        )

    token = token_parts[1]  # Extract actual JWT token

    try:
        # Decode and verify token signature
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])

        # Ensure the token has a "sub" (subject/user ID)
        if payload.get("sub") is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token is missing required claims."
            )

        # Convert payload into TokenData object
        return TokenData(
            id=payload.get("sub"),
            username=payload.get("email"),
            flag=payload.get("flag"),
            is_admin=payload.get("is_admin", False)  # Default to False if missing
        )

    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=401,  # ✅ Correct: Unauthorized (expired token)
            detail="Your token has expired. Please log in again or request a new one."
        )
    except jwt.InvalidSignatureError:
        raise HTTPException(
            status_code=403,  # 🔄 Changed to 403: Forbidden (tampered token)
            detail="Invalid token signature. Possible tampering detected."
        )
    except jwt.DecodeError:
        raise HTTPException(
            status_code=400,  # 🔄 Changed to 400: Bad Request (token format error)
            detail="Error decoding token. Token format is invalid."
        )
    except jwt.InvalidIssuerError:
        raise HTTPException(
            status_code=403,  # 🔄 Changed to 403: Forbidden (wrong token issuer)
            detail="Invalid token issuer. Access denied."
        )
    except jwt.InvalidAudienceError:
        raise HTTPException(
            status_code=403,  # 🔄 Changed to 403: Forbidden (wrong audience claim)
            detail="Invalid token audience. Access denied."
        )
    except jwt.ImmatureSignatureError:
        raise HTTPException(
            status_code=401,  # ✅ Correct: Unauthorized (token used before valid time)
            detail="Token is not yet valid. Check issued-at time (iat)."
        )
    except jwt.MissingRequiredClaimError:
        raise HTTPException(
            status_code=400,  # ✅ Correct: Bad Request (missing claims)
            detail="Token is missing a required claim. Ensure it includes sub, exp, iss, and aud."
        )
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=401,  # ✅ Correct: Unauthorized (generic invalid token)
            detail="Invalid token. Could not validate user credentials."
        )




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
async def get_current_user(request: Request,db : Annotated[Session, Depends(get_db)]):
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


