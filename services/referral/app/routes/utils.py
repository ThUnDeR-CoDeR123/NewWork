import hashlib
import random
import string
from fastapi import  HTTPException, Depends,status
from app.config import settings  # Assuming you have a DB session dependency
import httpx
from app.schemas import TokenData
from fastapi.security import OAuth2PasswordBearer


def generate_referral_code(user_id: int) -> str:

    base_string = f"{user_id}"

    hash_object = hashlib.sha256(base_string.encode())

    hash_digest = hash_object.hexdigest()[:8]  
    
    random_string = ''.join(random.choices(string.ascii_uppercase + string.digits, k=4))
    
    referral_code = f"{hash_digest}{random_string}"
    
    return referral_code



oauth2_scheme = OAuth2PasswordBearer(tokenUrl=settings.auth_service_url + "/create_token")


async def getTokenDataFromAuthService(token:str = Depends(oauth2_scheme)): #the functionality is changed to return the tokendata
    print(1)
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
    token_data = TokenData(id=int(response.json().get("id")),username=response.json().get("username"),flag=response.json().get("flag"),is_admin=response.json().get("is_admin"))
    if token_data.id is None:
            raise HTTPException(status_code=404, detail="User not found")
    return token_data


async def get_admin_user(token_data: TokenData = Depends(getTokenDataFromAuthService)):
    if not token_data.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    return token_data


async def get_normal_user(token_data: TokenData = Depends(getTokenDataFromAuthService)):
    if token_data.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admins are not allowed to access this resource"
        )
    return token_data