from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from app.schemas import Token,forgetEmail,LoginRequest,TokenRequest,TokenData
from app.database import get_db
from app.crud import getUserById,updatePassword,getUserByEmail,updateLastLogin,setForgetToken
from typing import Annotated
from jwt.exceptions import InvalidTokenError
from app.jwt import verify_token,create_access_token,authenticate_user,get_password_hash
from app.config import settings
import jwt
from starlette.responses import JSONResponse
import httpx


router = APIRouter(prefix="/api/v1/auth")


@router.get("/health")
async def health():
    return {'status':"OK AUTH"}


def generateToken(id:int,username:str,flag:str,is_admin:bool=False):
    return create_access_token(data={"sub": id, "email": username, "is_admin" : is_admin}, flag=flag)

# THIS ROUTE HANDELS LOGIN REQUESTS
# @router.post("/create_token")
# async def login_for_access_token(token_data: TokenRequest,db: Annotated[Session, Depends(get_db)],):
#     print("Create access token called: " + token_data.username)
#     try:
#         access_token = create_access_token(data={"sub": token_data.id, "email": token_data.username, "is_admin" : token_data.is_admin}, flag=token_data.flag)
#         print("Access token created by gateway: ")
#     except Exception as e:
#         print(str(e))
#         raise HTTPException(
#             status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
#             detail="INTERNAL SERVER ERROR",
#             headers={"WWW-Authenticate": "Bearer"},
#         )
    
#     # updateLastLogin(user,db)

#     return Token(access_token=access_token, token_type="bearer")


# verify token route

# @router.post("/verify_token")
async def get_current_user(request: Request, db: Annotated[Session, Depends(get_db)]):
    print("Inside the function ger_Current_user")
    try:
        # print(token)
        token_data = verify_token(request)
        if not token_data:
            return None
        print("gateway token: ",token_data.id,token_data.username,token_data.flag,token_data.is_admin)
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

    

@router.post("/forget-password" )
async def forget_password(req: forgetEmail,  db: Annotated[Session, Depends(get_db)]):

    user = getUserByEmail(req.email,db)

    try:
        access_token =  generateToken(id=user.id, username=req.email, flag="FORGET")
        
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"message": f"An unexpected error occurred: {str(e)}"}
        )
    


    try :
        print("trying to set forget token")
        setForgetToken(req.email,db,access_token)
        print("sending email notification...")
        await send_mail(
                req.email,
                subject="Here is your Forget password link!",
                htmlbody=f"<p>if this is not triggered by you then Ignore the email </p><br> click the button to reset your password : <a href='#'>Click Here!</a>"
            )
        print("email sent successfully")
        return JSONResponse(
                status_code=200, 
                content={
                    "message": "Email sent successfully!",
                    "link": f"#?token=%22{access_token}%22",
                    "token": f"{access_token}"
                }
            )
    except Exception as e:
        return JSONResponse(status_code=502, content={
            "message": "Could not send email ",
            "details": f"{str(e)}",
            "link": f"#?token=%22{access_token}%22",
            "token": f"{access_token}"
            })
        
@router.post("/login")
async def userLogin(
    form_data: LoginRequest, db : Annotated[Session , Depends(get_db) ]):

    #HERE THE REQUEST THAT IS BEING SENT TO AUTH IS IN {"username": "example@abc.com", "password": "somepassword"}
    print("inside my /login route")
    
    user =  authenticate_user(form_data.email, form_data.password, db=db)
    if not user :
        return JSONResponse(status_code=401,content={"message":"Invalid Credentials!"})
    if user.is_admin:
        return JSONResponse(status_code=401,content={"message":"Admin not found!"})
    if not user.is_verified:
        return JSONResponse(status_code=401,content={"message":"User not verified!"})
    
    try:
        print("generating token")
        access_token = generateToken(id=user.id, username=form_data.email,flag="LOGIN",is_admin=user.is_admin)
        
        print("returning JSONResponse")
        updateLastLogin(user,db)

        # Successfully return the token or relevant response from auth service
        return Token(access_token=access_token, token_type="bearer")


    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": f"An unexpected error occurred: {str(e)}"}
        )

async def send_mail(email: str,subject: str,htmlbody: str, from_email : str = None):

    #mail configuration
    payload = {
        "sender": {
                "name": settings.mail_from_name,
                "email": settings.mail_from
            },
        "to": [
                {
                    "email": email,
                }
            ],
        "subject": subject,
        "htmlContent": htmlbody
    }

    if from_email:
        payload["to"][0].email = from_email

    headers = {
    "accept": "application/json",
    "api-key": settings.brevo_api_key,
    "content-type": "application/json"
    }

    # Make the POST request
    with httpx.Client() as client:
        response = client.post(settings.smtp_api_url, json=payload, headers=headers)

    return response





# @router.post("/forgot-password",response_model=ResetToken)
# async def forgot_password(data : ForgotPasswordRequest,db: Annotated[Session, Depends(get_db)]):
    
#     user = getUserByEmail(email=data.email, db=db)
#     if not user:
#         raise HTTPException(status_code=404, detail="User not found")

#     token = create_access_token(data={"sub": user.id, "email": user.email},flag="FORGET")
    
#     return ResetToken(reset_token= token)



# @router.post("/reset-password")
# async def update_password(data:ResetPasswordRequest,db: Annotated[Session, Depends(get_db)]):
#     try:
        
#         token_data = verify_token(data.token)
        
#         print(token_data)
#         if token_data.flag != "FORGET":
#             raise HTTPException(status_code=403, detail="Supplied Token is not for Password Reset")
        
#         # Update the user's password in the database
#         # new_hash = get_password_hash(data.new_password)
#         # updatePassword(token_data.id,new_hashed_password=new_hash,db=db)
        
#         return TokenData(id=token_data.id,username=token_data.username,flag=token_data.flag)
    
#     except jwt.ExpiredSignatureError:
#         raise HTTPException(status_code=400, detail="Token expired")

#     except jwt.PyJWTError:
#         raise HTTPException(status_code=400, detail="Invalid token")