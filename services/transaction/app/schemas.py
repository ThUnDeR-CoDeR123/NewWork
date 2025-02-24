
from pydantic import BaseModel
from typing import Optional, List, Union

class transactionRequest(BaseModel):
    amount: float


class TokenData(BaseModel):
    id : int | None = None
    username: str | None = None
    flag: str = None
    is_admin: bool = False


class setMinBalance(BaseModel):
    balance : float = 0

class TransactionFilter(BaseModel):
    user_id: Optional[Union[str, int]] = None
    status: Optional[int] = None  # 0 for pending, 1 for approved, -1 for rejected
    from_date: Optional[str] = None
    to_date: Optional[str] = None
    page: int = 1
    limit: int = 10
    transaction_type: Optional[int] = None # 0 from credit, 1 for debit

class approveTransition(BaseModel):
    transaction_id: int
    status: int