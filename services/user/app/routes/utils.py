from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.orm import Session
from app.database import get_db

from app.schemas import  User,Token,LoginRequest,UserCreate,TokenData,Token,conversationData
from app.crud.user import createUser,authenticate_user,updateLastLogin,updateVerified,getUserById,get_level_counts
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from typing import Annotated
from app.config import settings
import httpx
from starlette.responses import JSONResponse
import asyncio
import app.schemas
from datetime import timedelta

router = APIRouter(prefix="/api/v1/user")

oauth2_scheme = OAuth2PasswordBearer("/login")




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

    # Print the response
    # print("response status code for the mail api : ",response.status_code)
    # print("response json for the mail api : ",response.json())

    return response



# this function maps data from user model defined in models.py to the user schema defined in schema.py
def modelToSchema(user : app.models.User,hierarchy_count:int = None,db:Session = None):
    
    UserSchema = User(
        id=user.id,
        full_name=user.full_name,
        email=user.email,
        is_verified=user.is_verified,
        last_login=(user.last_login + timedelta(hours=5, minutes=30)) if user.last_login else None,
        created_at=user.created_at + timedelta(hours=5, minutes=30),
        updated_at=(user.updated_at + timedelta(hours=5, minutes=30)) if user.updated_at else None,
        entitlements=user.entitlements,
        referral_code=user.referral_code,
        Crypto_balance=user.crypto_wallet.balance,
        Referral_balance=user.referral_wallet.balance,
        wallet_id=user.wallet_id,
        transaction_id=user.transaction_id,
        interim_balance=user.interim_wallet.balance
    )
    if db:
        levelCount = get_level_counts(db,user.id)
        if levelCount:
            UserSchema.level_count = [{"level": level, "count": count} for level, count in levelCount]
            
            
    if hierarchy_count:
        UserSchema.hierarchy_count = hierarchy_count
    return UserSchema


async def getTokenDataFromAuthService(token: str): #the functionality is changed to return the tokendata
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


async def generate_referral_code(user_id:int):
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{settings.referral_service_url}/create",
            json={"user_id":user_id}
        )
    return response


async def generate_referral(user_id:int,referral_code:str):
    print("Calling generate_referral for user in referral service...")
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{settings.referral_service_url}/add",
            json={
                    "referrer_code": referral_code,
                    "referred_user_id": user_id
                }
        )
    print("Returning response from referral-service...")
    return response


async def generateToken(id : int, username : str, flag : str,is_admin : bool=False):
    # return "this is token"
    print("calling the gateway service for generating token...")
    async with httpx.AsyncClient() as client:
        print(f"Auth service URL: {settings.auth_service_url}/create_token")

        response = await client.post(
            f"{settings.auth_service_url}/create_token",
                json={            
                    "id": id,
                    "username": username,
                    "flag" : flag,
                    "is_admin" : is_admin
                }
        )  
        if response.status_code != 200:
            print("Error creating token for user login")
    return response


@router.get("/health")
async def health():
    return {'status':"OK"}




# HERE THE REQUEST BODY COMES AS {"email": "example@example.com","password":"somepassword"}
@router.post("/login")
async def userLogin(
    form_data: LoginRequest, db : Annotated[Session , Depends(get_db) ]):

    #HERE THE REQUEST THAT IS BEING SENT TO AUTH IS IN {"username": "example@abc.com", "password": "somepassword"}
    print("inside my /login route")
    print(settings.auth_service_url)
    user =  authenticate_user(form_data.email, form_data.password, db=db)
    if not user :
        return JSONResponse(status_code=401,content={"error":"Invalid Credentials!"})
    if user.is_admin:
        return JSONResponse(status_code=401,content={"error":"Admin not found!"})
    if not user.is_verified:
        return JSONResponse(status_code=401,content={"error":"User not verified!"})
    
    try:
        print("generating token")
        response = await generateToken(id=user.id, username=form_data.email,flag="LOGIN",is_admin=user.is_admin)
        
        print("token generated")
        # If the status code isn't 200 OK but no error was raised
        if response.status_code != 200:
            if response.status_code == 401:
                return JSONResponse(
                    status_code=401,
                    content={"error": "Unauthorized: The provided credentials are incorrect or expired."}
                )
            print("status returned is not 200 OK")
            return JSONResponse(
                status_code=response.status_code,
                content={"error": "Unexpected status code returned from auth service."}
            )
        print("returning JSONResponse")
        updateLastLogin(user,db)

        # Successfully return the token or relevant response from auth service
        return response.json()

    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": f"An unexpected error occurred: {str(e)}"}
        )

@router.post("/conversation")
async def conversation(data : conversationData):
    email_body_user = f"""
<div>
    <div>Dear {data.name},</div>
    <p>Thank you for contacting us. We have received your query and will address it as soon as possible. Below are the details of your query for your reference:</p>
    <div>
        <p><strong>Name:</strong> {data.name}</p>
        <p><strong>Email:</strong> {data.email}</p>
        <p><strong>Query Description:</strong></p>
        <p>{data.query}</p>
    </div>
    <p>Our support team is reviewing your request, and you can expect a response within 24-48 hours. If you need to provide additional details or have urgent concerns, please feel free to reply to this email.</p>
    <div>
        <p>We value your time and thank you for choosing us.</p>
        <p>Warm regards,</p>
        <p><strong>Inddigi Team</strong></p>
    </div>
</div>
"""
    email_body_support = f"""
    - Name: {data.name}
    - Email: {data.email}
    - Query Description: 
      {data.query}"""
    marker =0
    try:

        await send_mail("customer.support@inddigi.com", "USER query", email_body_support,"business@inddigi.com")
        marker+=1
        await send_mail(data.email,f"Thank You for Reaching Out, {data.name}!", htmlbody = email_body_user)

        return JSONResponse(content = {"message":"success"},status_code = 200)

    except Exception as e :
        if marker == 0 :
            return JSONResponse(content = {"message":"error","details" : "support mail is not sent", "error":str(e)},status_code = 503)
        elif marker ==1:
            return JSONResponse(content = {"message":"success","details" : "customer mail is not sent", "error":str(e)},status_code = 200)
            
        else:
            return JSONResponse(content = {"message":"error", "details": "Couldn't send the email.", "error": str(e)},status_code = 503)

#Create User Account
@router.post("/register")
async def create_user(user: UserCreate,user_id: Annotated[int, Depends(createUser)]):

    #code for generating referral code
    try:
        response = await generateToken(id=user_id, username=user.email,flag="SIGNUP")

        if response.status_code != 200:
            return JSONResponse(status_code=response.status_code, content={"message": "Could not generate token for user. Please try again."})
    except Exception as e:
        return JSONResponse(status_code=500, content={"message": "Could not generate token for user. Please try again.",
                                                      "details": str(e)})
    try:  
        print("awaiting completion for mail sending...")

        await send_mail(email=user.email, 
                        subject="Account Created! Please Complete the Account Verification",
                        htmlbody=f"<p>Thanks for registering.</p><br> Click Here To Verify your account  <a href='http%22'>Click Here!</a>"
                        )
        print("mail sent successfully")
        r
        # await generate_referral_code(user_id)
        if not user.referral_code:
            return JSONResponse(status_code=200, content={"message": "Account Created! An email has been sent. No Referral Code Provided",
                                                          "token": response.json().get("access_token")})
        print("generating referral code...")
        assign_referral = await generate_referral(user_id,user.referral_code)
        print("Received Referral Code.")
        if assign_referral.status_code != 200:
            return JSONResponse(status_code=200, content = {"message": "user Created!, Invalid referral code",
                                                          "token": response.json().get("access_token")})
           
        return JSONResponse(status_code=200, content={"message": "Account Created! An email has been sent",
                                                          "token": response.json().get("access_token")})
    except Exception as e:
        return JSONResponse(status_code=200,  content={"message": "Could not send email! Please reverify",
                                                          "token": response.json().get("access_token")})



@router.post("/verify_user")
async def verify_email(data : Token,db : Annotated[Session , Depends(get_db) ]):
    # Fetch the user from the database
    token_data = await getTokenDataFromAuthService(data.token)
    print(token_data)
    if token_data.flag != "SIGNUP":
        return JSONResponse(
        status_code=401,
        content={
            "error": "Invalid token",
            "message": "The provided token is invalid or expired. Please request a new token."
            }
        )
    
    updateVerified(token_data.id,db)
    return {"message": "user verified successfully!"}



@router.post("/admin/login")
async def adminLogin(
    form_data: LoginRequest, db : Annotated[Session , Depends(get_db) ]):

    #HERE THE REQUEST THAT IS BEING SENT TO AUTH IS IN {"username": "example@abc.com", "password": "somepassword"}

    print(settings.auth_service_url)
    user =  authenticate_user(form_data.email, form_data.password, db=db)

    if not user :
        return JSONResponse(status_code=401,content="Invalid Credentials!")

    if not user.is_admin:
        return JSONResponse(status_code=401,content="Admin not found!")
    
    try:
        response = await generateToken(id=user.id, username=form_data.email,flag="LOGIN",is_admin=user.is_admin)
        
        
        # If the status code isn't 200 OK but no error was raised
        if response.status_code != 200:
            if response.status_code == 401:
                return JSONResponse(
                    status_code=401,
                    content={"error": "Unauthorized: The provided credentials are incorrect or expired."}
                )
            return JSONResponse(
                status_code=response.status_code,
                content={"error": "Unexpected status code returned from auth service."}
            )
        updateLastLogin(user,db)

        # Successfully return the token or relevant response from auth service
        return response.json()

    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": f"An unexpected error occurred: {str(e)}"}
        )


