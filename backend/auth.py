
from datetime import datetime, timedelta, timezone
import os

from fastapi import APIRouter, HTTPException, status
from passlib.context import CryptContext
from jose import JWTError, jwt
from pydantic import BaseModel, EmailStr, Field, field_validator
from pymongo.errors import PyMongoError, DuplicateKeyError

from backend.database import users_collection


router = APIRouter(
    prefix="/auth",
    tags=["Authentication"]
)


# --------------------------------------------------
# Password hashing
# --------------------------------------------------

pwd_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto"
)


# --------------------------------------------------
# JWT configuration
# --------------------------------------------------

SECRET_KEY = os.getenv("JWT_SECRET")

if not SECRET_KEY:
    raise ValueError(
        "JWT_SECRET is not set in the .env file"
    )

ALGORITHM = "HS256"

ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24


# --------------------------------------------------
# Request schemas
# --------------------------------------------------

class SignupRequest(BaseModel):

    username: str = Field(
        min_length=3,
        max_length=30
    )

    email: EmailStr

    password: str = Field(
        min_length=8,
        max_length=72
    )

    role: str

    @field_validator("username")
    @classmethod
    def validate_username(cls, value):

        value = value.strip()

        if not value:
            raise ValueError(
                "Username cannot be empty"
            )

        return value

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value):

        return value.strip().lower()

    @field_validator("role")
    @classmethod
    def validate_role(cls, value):

        value = value.strip().lower()

        allowed_roles = ["farmer", "buyer"]

        if value not in allowed_roles:
            raise ValueError(
                "Role must be either farmer or buyer"
            )

        return value


class LoginRequest(BaseModel):

    email: EmailStr

    password: str = Field(
        min_length=1,
        max_length=72
    )

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value):

        return value.strip().lower()


# --------------------------------------------------
# Password functions
# --------------------------------------------------

def hash_password(password: str) -> str:

    return pwd_context.hash(password)


def verify_password(
    plain_password: str,
    hashed_password: str
) -> bool:

    try:
        return pwd_context.verify(
            plain_password,
            hashed_password
        )

    except Exception:
        return False


# --------------------------------------------------
# JWT functions
# --------------------------------------------------

def create_access_token(
    user_id: str,
    email: str,
    role: str
):

    expire = datetime.now(
        timezone.utc
    ) + timedelta(
        minutes=ACCESS_TOKEN_EXPIRE_MINUTES
    )

    payload = {
        "sub": user_id,
        "email": email,
        "role": role,
        "exp": expire
    }

    return jwt.encode(
        payload,
        SECRET_KEY,
        algorithm=ALGORITHM
    )


# --------------------------------------------------
# Signup
# --------------------------------------------------

@router.post(
    "/signup",
    status_code=status.HTTP_201_CREATED
)
def signup(data: SignupRequest):

    try:

        # Check for existing email
        existing_user = users_collection.find_one({
            "email": data.email
        })

        if existing_user:

            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Email already registered"
            )

        # Check for existing username
        existing_username = users_collection.find_one({
            "username": data.username
        })

        if existing_username:

            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Username already taken"
            )

        # Create user document
        user = {
            "username": data.username,
            "email": data.email,
            "password_hash": hash_password(
                data.password
            ),
            "role": data.role,
            "created_at": datetime.now(timezone.utc)
        }

        result = users_collection.insert_one(user)

        return {
            "message": "Account created successfully",
            "user_id": str(result.inserted_id),
            "role": data.role
        }

    except HTTPException:
        raise

    except DuplicateKeyError:

        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email or username already registered"
        )

    except PyMongoError:

        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database service unavailable"
        )


# --------------------------------------------------
# Login
# --------------------------------------------------

@router.post("/login")
def login(data: LoginRequest):

    try:

        user = users_collection.find_one({
            "email": data.email
        })

        if not user:

            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password"
            )

        if not verify_password(
            data.password,
            user.get("password_hash", "")
        ):

            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password"
            )

        token = create_access_token(
            user_id=str(user["_id"]),
            email=user["email"],
            role=user["role"]
        )

        return {
            "message": "Login successful",
            "access_token": token,
            "token_type": "bearer",
            "user": {
                "id": str(user["_id"]),
                "username": user["username"],
                "email": user["email"],
                "role": user["role"]
            }
        }

    except HTTPException:
        raise

    except PyMongoError:

        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database service unavailable"
        )
