from sqlalchemy.orm import Session
from db.models.user import User
from db.models.api_key import ApiKey


class UserRepository:
    def __init__(self, db: Session):
        self.db = db

    def create_user(self, user: User):
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        return user

    def get_user_from_stripe_id(self, stripe_id: str) -> User | None:
        return self.db.query(User).filter(User.stripe_id == stripe_id).first()

    def update_user(self, user_id: int, update_data: dict) -> User | None:
        """Update user with dict of fields"""
        existing_user = self.get_user_by_id(user_id)
        if not existing_user:
            return None
        for key, value in update_data.items():
            if hasattr(existing_user, key):
                setattr(existing_user, key, value)
        self.db.commit()
        self.db.refresh(existing_user)
        return existing_user

    def get_user_by_email(self, email: str):
        return self.db.query(User).filter(User.email == email).first()

    def get_user_by_id(self, user_id: int):
        return self.db.query(User).filter(User.id == user_id).first()

    def list_users(self, limit: int = None):
        """Get all users, optionally limited"""
        query = self.db.query(User)
        if limit:
            query = query.limit(limit)
        return query.all()

    def delete_user(self, user_id: int):
        """Delete a user"""
        user = self.get_user_by_id(user_id)
        if user:
            self.db.delete(user)
            self.db.commit()
            return True
        return False

    def create_api_key(self, api_key: ApiKey):
        self.db.add(api_key)
        self.db.commit()
        self.db.refresh(api_key)
        return api_key

    def list_api_keys(self, user_id: int):
        return self.db.query(ApiKey).filter(ApiKey.user_id == user_id).all()

    def count_api_keys(self, user_id: int):
        return self.db.query(ApiKey).filter(ApiKey.user_id == user_id).count()

    def get_api_key(self, api_key_id: int):
        return self.db.query(ApiKey).filter(ApiKey.id == api_key_id).first()

    def get_api_key_by_key(self, api_key: str):
        return self.db.query(ApiKey).filter(ApiKey.api_key == api_key).first()

    def delete_api_key(self, api_key_id: int):
        api_key = self.get_api_key(api_key_id)
        if api_key:
            self.db.delete(api_key)
            self.db.commit()
