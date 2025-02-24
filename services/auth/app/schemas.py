from pydantic import BaseModel, EmailStr

class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    id : int | None = None
    username: str | None = None
    flag: str = None
    is_admin: bool = False


class TokenRequest(BaseModel):
    username: str
    id: int
    flag: str 
    is_admin: bool = False


class ForgotPasswordRequest(BaseModel):
    email: EmailStr 


class ResetToken(BaseModel):
    reset_token: str 


class ResetPasswordRequest(BaseModel):
    token : str
    new_password: str