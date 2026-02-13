from pydantic import BaseModel
from datetime import datetime


class AccountCreate(BaseModel):
    name: str
    balance: float = 0.0


class AccountResponse(BaseModel):
    id: str
    name: str
    balance: float
    created_at: datetime

    class Config:
        orm_mode = True


class TransactionCreate(BaseModel):
    amount: float


class TransactionResponse(BaseModel):
    id: str
    account_id: str
    type: str
    amount: float
    status: str
    created_at: datetime

    class Config:
        orm_mode = True
