from typing import Optional, List
from pydantic import BaseModel, EmailStr, Field
from datetime import datetime,timezone

# Schemas for Entitlement
class EntitlementBase(BaseModel):
    label: str
    description: Optional[str] = None

class EntitlementCreate(EntitlementBase):
    pass


class TokenData(BaseModel):
    id : int | None = None
    username: str | None = None
    flag: str = None
    is_admin: bool = False

class EntitlementUpdate(EntitlementBase):
    pass

class Entitlement(EntitlementBase):
    id: int
    user_id: int

    class Config:
        from_attributes = True

# Schemas for User
class UserBase(BaseModel):
    email: str
    full_name: Optional[str] = None
    last_login: Optional[datetime] = None

class UserCreate(UserBase):
    password: str
    referral_code: Optional[str] = None
    
class updateWalletId(BaseModel):
    token_data: Optional[TokenData] = None
    wallet_id: str = None
    
class conversationData(BaseModel):
    name: str
    email: str
    query: str

class User(UserBase):
    id: int
    created_at: datetime
    updated_at: datetime
    entitlements: Optional[List[Entitlement]] = Field(default_factory=list)
    wallet_id: Optional[str] = None
    is_verified: Optional[bool] = False
    referral_code: Optional[str] = None
    interim_balance: Optional[float] = 0.0
    Crypto_balance: Optional[float] = 0.0
    Referral_balance: Optional[float] = 0.0
    transaction_id: Optional[str] = None
    hierarchy_count: Optional[int] = None
    level_count : Optional[List[dict]] = Field(default_factory=list)
    plans: Optional[List[dict]] = Field(default_factory=list)

    class Config:
        from_attributes = True

    
class UserUpdate(UserBase):
    token_data : Optional[TokenData] = None
    email : Optional[str] = None
    is_verified: Optional[bool] = False
    is_admin: Optional[bool] = False
    referral_code: Optional[str] = None
    Crypto_balance: Optional[float] = 0.0
    Referral_balance: Optional[float] = 0.0
    transaction_id: Optional[str] = None


class UserFilter(BaseModel):
    token_data : Optional[TokenData] = None
    page: Optional[int] = None
    limit: Optional[int] = None
    email : Optional[str] = None
# Schemas for Wallet
class WalletBase(BaseModel):
    ammy: float
    meta: Optional[str] = None

class WalletCreate(WalletBase):
    pass

class WalletUpdate(WalletBase):
    pass

class Wallet(WalletBase):
    id: int
    user_id: int

    class Config:
        from_attributes = True

class DeleteUser(BaseModel):
    msg: str
    username : str

class Token(BaseModel):
    access_token: str
    token_type: str
    class Config:
        from_attributes = True

# class TokenData(BaseModel):
#     username: str | None = None

class OTP(BaseModel):
    otp : str
    
class OTPdetails(OTP):
    id: int
    email: str
    # token : Optional[str] = None


class LoginRequest(BaseModel):
    email: str
    password: str


class passwordReset(BaseModel):
    token_data : Optional[TokenData] = None
    token: str
    new_password: str

class forgetEmail(BaseModel):
    email: str

class VerifyEmail(forgetEmail):
    otp : str


class Token(BaseModel):
    token : str | None = None

