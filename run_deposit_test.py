import requests
from db.database import SessionLocal
from db.models import User
from auth import create_access_token, get_password_hash

BACKEND = "http://localhost:8001/api"

def ensure_test_user(email="test+auto@example.com", username="autotest", password="password123"):
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.email == email).first()
        if user:
            return user

        hashed = get_password_hash(password)
        user = User(email=email, username=username, password_hash=hashed)
        db.add(user)
        db.commit()
        db.refresh(user)
        return user
    finally:
        db.close()

def main():
    user = ensure_test_user()
    token = create_access_token({"user_id": user.user_id})

    payload = {
        "amount": 100,
        "currency": "USD",
        "payment_method": "card"
    }

    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

    print(f"Using token for user_id={user.user_id}: {token[:20]}...")

    resp = requests.post(f"{BACKEND}/payments/deposit/initiate", json=payload, headers=headers, timeout=30)

    print("Status:", resp.status_code)
    try:
        print("Body:", resp.json())
    except Exception:
        print("Body (text):", resp.text)

if __name__ == '__main__':
    main()
