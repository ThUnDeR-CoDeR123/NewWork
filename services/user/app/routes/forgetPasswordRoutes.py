from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.orm import Session
from app.schemas import   User,Token,DeleteUser,OTP,passwordReset,forgetEmail,TokenData
from app.database import get_db
from app.crud.user import getUserByEmail,get_password_hash,updatePassword,setForgetToken, checkForgetToken
from typing import Annotated,List
from app.routes.utils import send_mail,generateToken,getTokenDataFromAuthService
from app.config import settings
import httpx
from http import HTTPStatus
from starlette.responses import JSONResponse

forgetRouter= APIRouter(prefix="/api/v1/user")



@forgetRouter.post("/forget-password" )
async def forget_password(req: forgetEmail, background_tasks: BackgroundTasks, db: Annotated[Session, Depends(get_db)]):

    user = getUserByEmail(req.email,db)

    try:
        response = await generateToken(id=user.id, username=req.email, flag="FORGET")
        if response.status_code != 200:
            status_info = HTTPStatus(response.status_code)
            return JSONResponse(
                status_code=status_info.value,
                content={"error": f"{status_info.phrase}: {status_info.description}"}
            )
    except httpx.RequestError as exc:
        return JSONResponse(
            status_code=500,
            content={"error": f"An error occurred while requesting {exc.request.url}: {str(exc)}"}
        )
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": f"An unexpected error occurred: {str(e)}"}
        )
    


    try :

        setForgetToken(req.email,db,response.json().get('access_token'))
        await send_mail(
                req.email,
                subject="Here is your Forget password link!",
                htmlbody=f"<p>if this is not triggered by you then Ignore the email </p><br> click the button to reset your password : <a href='https://inddigi.com/#/confirmpass?token=%22{response.json().get('access_token')}%22'>Click Here!</a>"
            )
        return JSONResponse(
                status_code=200, 
                content={
                    "message": "Email sent successfully!",
                    "link": f"https://inddigi.com/#/confirmpass?token=%22{response.json().get('access_token')}%22",
                    "token": f"{response.json().get('access_token')}"
                }
            )
    except Exception as e:
        return JSONResponse(status_code=502, content={
            "message": "Could not send email ",
            "details": f"{str(e)}",
            "link": f"https://inddigi-dev.web.app/#/confirmpass?token=%22{response.json().get('access_token')}%22",
            "token": f"{response.json().get('access_token')}"
            })
        


@forgetRouter.post("/reset-password")
async def reset_password(data: passwordReset, db: Annotated[Session, Depends(get_db)]):
    try:
        # token_data = await getTokenDataFromAuthService(data.token)
        token_data = data.token_data

        l=checkForgetToken(token_data.id,db, data.token)
        print(l)
        if l[0]!=l[1] :
            return JSONResponse(
                status_code=403,
                content={"error": "Supplied token is invalid."}
            )

        # Check if the flag indicates that this token is meant for password reset
        if token_data.flag != "FORGET":
            return JSONResponse(
                status_code=403,
                content={"error": "Supplied token is not for password reset."}
            )
        new_hash = get_password_hash(data.new_password)

        updatePassword(token_data.id, new_hashed_password=new_hash, db=db)

        return JSONResponse(
            status_code=200,
            content={"message": "Password reset successful"}
        )

    except httpx.RequestError as e:
        # Catching any network-related errors
        return JSONResponse(
            status_code=500,
            content={"error": f"Request to auth service failed: {str(e)}"}
        )

    except httpx.HTTPStatusError as e:
        # Handling non-200 responses from the auth service
        return JSONResponse(
            status_code=e.response.status_code,
            content={"error": "Failed to verify token with the auth service."}
        )

    except Exception as e:
        # Generic fallback for all unforeseen exceptions
        return JSONResponse(
            status_code=500,
            content={"error": f"An unexpected error occurred: {str(e)}"}
        )

