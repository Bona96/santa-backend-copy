import argparse
from db.database import SessionLocal
from db.models import User

def make_admin(email=None, user_id=None):
    db = SessionLocal()
    try:
        if email:
            user = db.query(User).filter(User.email == email).first()
        elif user_id:
            user = db.query(User).filter(User.user_id == int(user_id)).first()
        else:
            print("Provide --email or --user-id")
            return

        if not user:
            print("User not found")
            return

        user.is_admin = True
        db.add(user)
        db.commit()
        print(f"Set is_admin=True for user {user.user_id} ({user.email})")
    finally:
        db.close()

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--email', help='Email of user to promote to admin')
    parser.add_argument('--user-id', help='User id to promote to admin')
    args = parser.parse_args()
    make_admin(email=args.email, user_id=args.user_id)
