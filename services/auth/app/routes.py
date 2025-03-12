from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.schemas import Token,ForgotPasswordRequest,ResetToken,ResetPasswordRequest,TokenRequest,TokenData
from app.database import get_db
from app.crud import getUserById,updatePassword,getUserByEmail,updateLastLogin
from fastapi.security import OAuth2PasswordRequestForm
from typing import Annotated
from jwt.exceptions import InvalidTokenError
from app.jwt import verify_token,oauth2_scheme,create_access_token,authenticate_user,get_password_hash
import jwt
from starlette.responses import JSONResponse



router = APIRouter(prefix="/api/v1/auth")


@router.get("/health")
async def health():
    return {'status':"OK AUTH"}


# THIS ROUTE HANDELS LOGIN REQUESTS
@router.post("/create_token")
async def login_for_access_token(token_data: TokenRequest,db: Annotated[Session, Depends(get_db)],):
    
    try:
        access_token = create_access_token(data={"sub": token_data.id, "email": token_data.username, "is_admin" : token_data.is_admin}, flag=token_data.flag)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="INTERNAL SERVER ERROR",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # updateLastLogin(user,db)

    return Token(access_token=access_token, token_type="bearer")


# verify token route

@router.post("/verify_token")
async def get_current_user(token: Annotated[str, Depends(oauth2_scheme)], db: Annotated[Session, Depends(get_db)]):
    try:
        # print(token)
        token_data = verify_token(token)

        # Return token data if the token is valid
        return TokenData(id=token_data.id, username=token_data.username, flag=token_data.flag,is_admin=token_data.is_admin)

    except jwt.ExpiredSignatureError:
        return JSONResponse(
            status_code=401,
            content={"message": "Your Forgetpassword/Login token is expired. Kindly relogin or make another forget password request."}
        )

    except jwt.InvalidSignatureError:
        return JSONResponse(
            status_code=401,
            content={"message": "Your AccessToken is invalid. Kindly relogin or try again."}
        )

    except jwt.DecodeError:
        return JSONResponse(
            status_code=500,
            content={"message": "Error decoding token."}
        )

    except jwt.InvalidIssuerError:
        return JSONResponse(
            status_code=401,
            content={"message": "Your AccessToken is invalid."}
        )

    except jwt.InvalidAudienceError:
        return JSONResponse(
            status_code=401,
            content={"message": "Invalid token audience."}
        )

    except jwt.ImmatureSignatureError:
        return JSONResponse(
            status_code=401,
            content={"message": "Token is not yet valid."}
        )

    except jwt.MissingRequiredClaimError:
        return JSONResponse(
            status_code=400,
            content={"message": "Token is missing a required claim."}
        )

    except jwt.InvalidTokenError:
        return JSONResponse(
            status_code=401,
            content={"message": "Could not validate user credentials."}
        )

    





@router.post("/forgot-password",response_model=ResetToken)
async def forgot_password(data : ForgotPasswordRequest,db: Annotated[Session, Depends(get_db)]):
    
    user = getUserByEmail(email=data.email, db=db)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    token = create_access_token(data={"sub": user.id, "email": user.email},flag="FORGET")
    
    return ResetToken(reset_token= token)



@router.post("/reset-password")
async def update_password(data:ResetPasswordRequest,db: Annotated[Session, Depends(get_db)]):
    try:
        
        token_data = verify_token(data.token)
        
        print(token_data)
        if token_data.flag != "FORGET":
            raise HTTPException(status_code=403, detail="Supplied Token is not for Password Reset")
        
        # Update the user's password in the database
        # new_hash = get_password_hash(data.new_password)
        # updatePassword(token_data.id,new_hashed_password=new_hash,db=db)
        
        return TokenData(id=token_data.id,username=token_data.username,flag=token_data.flag)
    
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=400, detail="Token expired")

    except jwt.PyJWTError:
        raise HTTPException(status_code=400, detail="Invalid token")