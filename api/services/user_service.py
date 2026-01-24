from passlib.context import CryptContext
from db.models.user import User
from db.models.api_key import ApiKey
from db.repositories.user_repository import UserRepository
import jwt
import os
from datetime import datetime, timedelta, timezone
import uuid
import logging
from fastapi import Request


class UserNotFoundException(Exception):
    pass


class UserServiceException(Exception):
    def __init__(self, detail):
        super().__init__(detail)
        self.detail = detail

    def __str__(self):
        return str(self.detail)


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    filename="log.txt",
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


class UserService:
    def __init__(self, user_repo: UserRepository):
        self.user_repo = user_repo
        # Use argon2 instead of bcrypt for better compatibility
        self.pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")
        # Load JWT_SECRET from .env (was SECRET_KEY)
        self.SECRET_KEY = os.getenv("JWT_SECRET", os.getenv("SECRET_KEY", "fixed-secret-key-for-cronpulse"))
        if not self.SECRET_KEY:
            logger.warning("JWT_SECRET not found in environment, using fallback")
        logger.info(
            f"Initialized UserService with SECRET_KEY: "
            f"{self.SECRET_KEY[:4]}... (truncated for security)"
        )
        self.ALGORITHM = "HS256"
        self.ACCESS_TOKEN_EXPIRE_MINUTES = 30

    def get_by_id(self, user_id: int) -> User:
        user = self.user_repo.get_user_by_id(user_id)
        if not user:
            logger.error(f"User with ID {user_id} not found")
            raise UserNotFoundException(f"User with ID {user_id} not found")
        logger.info(f"Retrieved user with ID {user_id}")
        return user

    def signup(self, email: str, password: str):
        if not email or "@" not in email:
            logger.error(f"Invalid email address: {email}")
            raise UserServiceException("Invalid email address")
        if len(password) < 6:
            logger.error("Password too short")
            raise UserServiceException("Password must be at least 6 characters long")
        existing_user = self.user_repo.get_user_by_email(email)
        if existing_user:
            logger.error(f"Email already registered: {email}")
            raise UserServiceException("Email already registered")
        hashed_password = self.pwd_context.hash(password)
        user = User(email=email, hashed_password=hashed_password)
        self.user_repo.create_user(user)
        logger.info(f"Created user with email {email}")
        return user

    def login(self, email: str, password: str):
        user = self.user_repo.get_user_by_email(email)
        if not user or not self.pwd_context.verify(password, user.hashed_password):
            logger.error(f"Login failed for email {email}: Invalid credentials")
            raise UserServiceException("Invalid credentials")
        access_token_expires = timedelta(minutes=self.ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = self.create_access_token(
            data={"sub": str(user.id)}, expires_delta=access_token_expires
        )
        ts = datetime.fromtimestamp(
            access_token_expires.total_seconds()
            + datetime.now(timezone.utc).timestamp()
        )
        logger.info(f"Generated token for user {user.id}, expires at {ts} UTC")
        return {
            "access_token": access_token,
            "token_type": "bearer",
            "user_id": user.id,
        }

    def create_access_token(self, data: dict, expires_delta: timedelta):
        to_encode = data.copy()
        expire = datetime.now(timezone.utc) + expires_delta
        to_encode.update({"exp": expire})
        encoded_jwt = jwt.encode(to_encode, self.SECRET_KEY, algorithm=self.ALGORITHM)
        logger.info(f"Created JWT with exp: {expire}")
        return encoded_jwt

    def get_current_user(self, token: str):
        logger.info(f"Decoding token: {token[:10]}... for current user")
        try:
            logger.info(f"Attempting to decode token: {token[:10]}...")
            payload = jwt.decode(token, self.SECRET_KEY, algorithms=[self.ALGORITHM])
            user_id = payload.get("sub")
            if user_id is None:
                logger.error("No user_id in token payload")
                raise UserServiceException("Not authenticated")
            try:
                user_id = int(user_id)
            except ValueError:
                logger.error(f"Invalid user_id format in token: {user_id}")
                raise UserServiceException("Not authenticated")
            user = self.user_repo.get_user_by_id(user_id)
            if user is None:
                logger.error(f"No user found for ID {user_id} in database")
                raise UserServiceException("Not authenticated")
            logger.info(f"Successfully authenticated user ID {user_id}")
            return user
        except jwt.ExpiredSignatureError:
            logger.error("Token has expired")
            raise UserServiceException("Token expired")
        except jwt.InvalidKeyError:
            logger.error(
                f"JWT decode failed: Invalid key, SECRET_KEY used: "
                f"{self.SECRET_KEY[:4]}..."
            )
            raise UserServiceException("Invalid authentication key")
        except jwt.PyJWTError as e:
            logger.error(f"JWT decode error: {str(e)}")
            raise UserServiceException("Not authenticated")

    def create_api_key(self, user_id: int, name: str):
        if not name or not name.strip():
            logger.error(f"API key name cannot be empty for user {user_id}")
            raise UserServiceException("API key name cannot be empty")
        api_key = str(uuid.uuid4())
        key_hash = self.pwd_context.hash(api_key)
        api_key_obj = ApiKey(
            user_id=user_id,
            api_key=api_key,
            key_hash=key_hash,
            name=name,
            created_at=datetime.now(timezone.utc),
        )
        self.user_repo.create_api_key(api_key_obj)
        logger.info(f"Created API key for user {user_id}")
        return api_key

    def list_api_keys(self, user_id: int):
        return self.user_repo.list_api_keys(user_id)

    def delete_api_key(self, api_key_id: int, user_id: int):
        api_key = self.user_repo.get_api_key(api_key_id)
        if not api_key or api_key.user_id != user_id:
            logger.error(f"Failed to delete API key {api_key_id}: Forbidden")
            raise UserServiceException("Forbidden")
        self.user_repo.delete_api_key(api_key_id)
        logger.info(f"Deleted API key {api_key_id} for user {user_id}")

    def validate_api_key(self, api_key: str):
        api_key_obj = self.user_repo.get_api_key_by_key(api_key)
        if not api_key_obj or not self.pwd_context.verify(
            api_key, api_key_obj.key_hash
        ):
            logger.error("Invalid API key")
            raise UserServiceException("Invalid API key")
        logger.info(f"Validated API key for user {api_key_obj.user_id}")
        return api_key_obj.user_id

    def count_api_keys(self, user_id: int):
        count = self.user_repo.count_api_keys(user_id)
        logger.info(f"Counted {count} API keys for user {user_id}")
        return count

    async def get_current_user_from_request(self, request: Request):
        logger.info("Extracting token from request cookies")
        token = request.cookies.get("access_token")
        logger.info(
            "Raw token from cookie: type=%s repr=%s", type(token).__name__, repr(token)
        )

        if not token:
            # try Authorization header fallback
            auth = request.headers.get("Authorization") or request.headers.get(
                "authorization"
            )
            if auth and isinstance(auth, str) and auth.lower().startswith("bearer "):
                token = auth.split(" ", 1)[1].strip()
                logger.info("Found token in Authorization header")
        if not token:
            logger.error("No access token found in request cookies or headers")
            raise UserServiceException("Not authenticated")

        # If bytes, decode
        if isinstance(token, (bytes, bytearray)):
            try:
                token = token.decode("utf-8")
            except Exception as e:
                logger.error("Token bytes decode error: %s", e)
                raise UserServiceException("Invalid token format")

        # If cookie contains JSON string (double quotes) try json
        if isinstance(token, str) and token.strip().startswith("{"):
            parsed = None
            try:
                import json

                parsed = json.loads(token)
            except Exception:
                # try Python literal dict (single quotes) using ast.literal_eval
                try:
                    import ast

                    parsed = ast.literal_eval(token)
                except Exception:
                    parsed = None
            if isinstance(parsed, dict):
                token = (
                    parsed.get("access_token")
                    or parsed.get("token")
                    or parsed.get("jwt")
                    or token
                )
                logger.info("Extracted token from embedded dict in cookie")

        # Handle "Bearer ..." stored accidentally
        if isinstance(token, str) and token.lower().startswith("bearer "):
            token = token.split(" ", 1)[1].strip()
            logger.info("Stripped 'Bearer' prefix from token")

        if not isinstance(token, str):
            logger.error("Token is not a string after extraction: %s", type(token))
            raise UserServiceException("Invalid token")

        logger.info(
            "Attempting to decode token: %s... for current user", repr(token)[:80]
        )
        try:
            return self.get_current_user(token)
        except Exception as e:
            logger.error("JWT decode error: %s", e)
            raise UserServiceException("Invalid credentials")
