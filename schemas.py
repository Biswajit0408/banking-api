from pydantic import BaseModel

class AccountCreate(BaseModel):
    name: str

class AccountResponse(BaseModel):
    id: str
    name: str
    balance: float

    class Config:
        from_attributes = True
