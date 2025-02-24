# schemas.py

from pydantic import BaseModel, Field
from typing import List, Optional

class CreateReferralRequest(BaseModel):
    user_id: int 

class ReferralAddRequest(BaseModel):
    referrer_code: str 
    referred_user_id: int


class TokenData(BaseModel):
    id : int | None = None
    username: str | None = None
    flag: str = None
    is_admin: bool = False


class UserFilter(BaseModel):
    token_data: Optional[TokenData] = None
    email : Optional[str] = None


