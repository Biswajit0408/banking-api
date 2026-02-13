from fastapi import FastAPI, Depends
from sqlalchemy.orm import Session
from fastapi import FastAPI, Depends, HTTPException
from fastapi import Query
from database import Base, engine, SessionLocal
from models import Account
from models import Account, Transaction
from schemas import (
    AccountCreate,
    AccountResponse,
    TransactionCreate,
    TransactionResponse
)


app = FastAPI(title="Simple Banking API")

Base.metadata.create_all(bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@app.get("/")
def root():
    return {"message": "Banking API is running"}


@app.post("/accounts", response_model=AccountResponse)
def create_account(
    account: AccountCreate,
    db: Session = Depends(get_db)
):
    new_account = Account(
        name=account.name,
        balance=account.balance
    )
    db.add(new_account)
    db.commit()
    db.refresh(new_account)
    return new_account


@app.get("/accounts/{account_id}", response_model=AccountResponse)
def get_account(
    account_id: str,   # UUID, not int
    db: Session = Depends(get_db)
):
    account = db.query(Account).filter(Account.id == account_id).first()

    if not account:
        return {"error": "Account not found"}

    return account

@app.post(
    "/accounts/{account_id}/deposit",
    response_model=AccountResponse
)
def deposit(
    account_id: str,
    transaction: TransactionCreate,
    db: Session = Depends(get_db)
):
    account = db.query(Account).filter(Account.id == account_id).first()

    if not account:
        return {"error": "Account not found"}

    if transaction.amount <= 0:
        return {"error": "Deposit amount must be positive"}

    account.balance += transaction.amount

    txn = Transaction(
        account_id=account.id,
        type="DEPOSIT",
        amount=transaction.amount,
        status="SUCCESS"
    )

    db.add(txn)
    db.commit()
    db.refresh(account)

    return account

@app.post(
    "/accounts/{account_id}/withdraw",
    response_model=AccountResponse
)
def withdraw(
    account_id: str,
    transaction: TransactionCreate,
    db: Session = Depends(get_db)
):
    account = db.query(Account).filter(Account.id == account_id).first()

    if not account:
        raise HTTPException(
            status_code=404,
            detail="Account not found"
        )

    if transaction.amount <= 0:
        raise HTTPException(
            status_code=400,
            detail="Withdraw amount must be positive"
        )

    if account.balance < transaction.amount:
        failed_txn = Transaction(
            account_id=account.id,
            type="WITHDRAW",
            amount=transaction.amount,
            status="FAILED"
        )
        db.add(failed_txn)
        db.commit()

        raise HTTPException(
            status_code=400,
            detail="Insufficient balance"
        )

    account.balance -= transaction.amount

    txn = Transaction(
        account_id=account.id,
        type="WITHDRAW",
        amount=transaction.amount,
        status="SUCCESS"
    )

    db.add(txn)
    db.commit()
    db.refresh(account)

    return account

@app.post("/transfer")
def transfer(
    from_account_id: str,
    to_account_id: str,
    amount: float,
    db: Session = Depends(get_db)
):
    if amount <= 0:
        raise HTTPException(
            status_code=400,
            detail="Transfer amount must be positive"
        )

    sender = db.query(Account).filter(Account.id == from_account_id).first()
    receiver = db.query(Account).filter(Account.id == to_account_id).first()

    if not sender or not receiver:
        raise HTTPException(
            status_code=404,
            detail="Invalid sender or receiver account"
        )

    if sender.balance < amount:
        raise HTTPException(
            status_code=400,
            detail="Insufficient balance"
        )

    try:
        # 1️⃣ Update balances
        sender.balance -= amount
        receiver.balance += amount

        # 2️⃣ Log transactions
        debit_txn = Transaction(
            account_id=sender.id,
            type="TRANSFER_DEBIT",
            amount=amount,
            status="SUCCESS",
            reference_id=receiver.id
        )

        credit_txn = Transaction(
            account_id=receiver.id,
            type="TRANSFER_CREDIT",
            amount=amount,
            status="SUCCESS",
            reference_id=sender.id
        )

        db.add_all([debit_txn, credit_txn])
        db.commit()

        return {
            "message": "Transfer successful",
            "from_account_id": sender.id,
            "to_account_id": receiver.id,
            "amount": amount
        }

    except Exception:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail="Transfer failed, rolled back"
        )

@app.get("/accounts", response_model=list[AccountResponse])
def list_accounts(
    limit: int = Query(10, ge=1, le=50),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db)
):
    return (
        db.query(Account)
        .order_by(Account.created_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )

@app.get(
    "/accounts/{account_id}/transactions",
    response_model=list[TransactionResponse]
)
def get_transactions(
    account_id: str,
    limit: int = Query(10, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db)
):
    return (
        db.query(Transaction)
        .filter(Transaction.account_id == account_id)
        .order_by(Transaction.created_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="127.0.0.1",
        port=8000,
        reload=True
    )
