from sqlalchemy.orm import Session
from fastapi import HTTPException
from models import Account, Transaction, IdempotencyKey

def transfer_money(
    db: Session,
    from_account_id: str,
    to_account_id: str,
    amount: float,
    idempotency_key: str
):
    if db.query(IdempotencyKey).filter(
        IdempotencyKey.key == idempotency_key
    ).first():
        return {"message": "Duplicate request ignored"}

    if amount <= 0:
        raise HTTPException(status_code=400, detail="Amount must be positive")

    sender = db.query(Account).filter(Account.id == from_account_id).first()
    receiver = db.query(Account).filter(Account.id == to_account_id).first()

    if not sender or not receiver:
        raise HTTPException(status_code=404, detail="Invalid account")

    if sender.balance < amount:
        raise HTTPException(status_code=400, detail="Insufficient balance")

    sender.balance -= amount
    receiver.balance += amount

    db.add_all([
        Transaction(
            account_id=sender.id,
            type="TRANSFER_DEBIT",
            amount=amount,
            status="SUCCESS",
            reference_id=receiver.id
        ),
        Transaction(
            account_id=receiver.id,
            type="TRANSFER_CREDIT",
            amount=amount,
            status="SUCCESS",
            reference_id=sender.id
        ),
        IdempotencyKey(key=idempotency_key)
    ])

    db.commit()
    return {"message": "Transfer successful"}
