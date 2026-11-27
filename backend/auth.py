
from datetime import datetime, timedelta, timezone
import os

from fastapi import APIRouter, HTTPException, status
from passlib.context import CryptContext
from jose import JWTError, jwt
from pydantic import (
    BaseModel,
    EmailStr,
    Field,
    field_validator,
)
from pymongo.errors import PyMongoError, DuplicateKeyError

from backend.database import users_collection


# ============================================================
# ROUTER
# ============================================================

router = APIRouter(
    prefix="/auth",
    tags=["Authentication"],
)


# ============================================================
# PASSWORD HASHING
# ============================================================

pwd_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto",
)


# ============================================================
# JWT CONFIGURATION
# ============================================================

SECRET_KEY = os.getenv("JWT_SECRET")

if not SECRET_KEY:
    raise RuntimeError(
        "JWT_SECRET is missing. Please configure it in your .env file."
    )

ALGORITHM = "HS256"

ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24


# ============================================================
# REQUEST SCHEMAS
# ============================================================

class SignupRequest(BaseModel):

    username: str = Field(
        min_length=3,
        max_length=30,
    )

    email: EmailStr

    password: str = Field(
        min_length=8,
    )

    role: str

    # --------------------------------------------------------
    # Username normalization
    # --------------------------------------------------------

    @field_validator("username")
    @classmethod
    def normalize_username(cls, value):

        value = value.strip()

        if not value:
            raise ValueError(
                "Username cannot be empty"
            )

        if len(value) < 3:
            raise ValueError(
                "Username must contain at least 3 characters"
            )

        if len(value) > 30:
            raise ValueError(
                "Username cannot exceed 30 characters"
            )

        return value

    # --------------------------------------------------------
    # Email normalization
    # --------------------------------------------------------

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value):

        return str(value).strip().lower()

    # --------------------------------------------------------
    # Password validation
    # --------------------------------------------------------

    @field_validator("password")
    @classmethod
    def validate_password(cls, value):

        if len(value.encode("utf-8")) > 72:
            raise ValueError(
                "Password cannot exceed 72 bytes"
            )

        if not value.strip():
            raise ValueError(
                "Password cannot be empty"
            )

        return value

    # --------------------------------------------------------
    # Role validation
    # --------------------------------------------------------

    @field_validator("role")
    @classmethod
    def validate_role(cls, value):

        value = value.strip().lower()

        allowed_roles = {
            "farmer",
            "buyer",
        }

        if value not in allowed_roles:
            raise ValueError(
                "Role must be either farmer or buyer"
            )

        return value


class LoginRequest(BaseModel):

    email: EmailStr

    password: str = Field(
        min_length=1,
    )

    # --------------------------------------------------------
    # Email normalization
    # --------------------------------------------------------

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value):

        return str(value).strip().lower()

    # --------------------------------------------------------
    # Password validation
    # --------------------------------------------------------

    @field_validator("password")
    @classmethod
    def validate_password(cls, value):

        if len(value.encode("utf-8")) > 72:
            raise ValueError(
                "Password cannot exceed 72 bytes"
            )

        return value


# ============================================================
# PASSWORD FUNCTIONS
# ============================================================

def hash_password(password: str) -> str:

    return pwd_context.hash(password)


def verify_password(
    plain_password: str,
    hashed_password: str,
) -> bool:

    try:

        if not hashed_password:
            return False

        return pwd_context.verify(
            plain_password,
            hashed_password,
        )

    except Exception:
        # Invalid/corrupted hash should never crash login.
        return False


# ============================================================
# JWT FUNCTIONS
# ============================================================

def create_access_token(
    user_id: str,
    email: str,
    role: str,
):

    expiration = datetime.now(
        timezone.utc
    ) + timedelta(
        minutes=ACCESS_TOKEN_EXPIRE_MINUTES
    )

    payload = {
        "sub": user_id,
        "email": email,
        "role": role,
        "exp": expiration,
    }

    token = jwt.encode(
        payload,
        SECRET_KEY,
        algorithm=ALGORITHM,
    )

    return token


def decode_access_token(token: str):

    try:

        payload = jwt.decode(
            token,
            SECRET_KEY,
            algorithms=[ALGORITHM],
        )

        user_id = payload.get("sub")
        email = payload.get("email")
        role = payload.get("role")

        if not user_id or not email or not role:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token payload",
            )

        if role not in {"farmer", "buyer"}:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid user role",
            )

        return payload

    except JWTError:

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )


# ============================================================
# SIGNUP
# ============================================================

@router.post(
    "/signup",
    status_code=status.HTTP_201_CREATED,
)
def signup(data: SignupRequest):

    # --------------------------------------------------------
    # 1. Check whether email already exists
    # --------------------------------------------------------

    try:

        existing_user = users_collection.find_one({
            "email": data.email,
        })

        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Email already registered",
            )

        # ----------------------------------------------------
        # 2. Check whether username already exists
        # ----------------------------------------------------

        existing_username = users_collection.find_one({
            "username": data.username,
        })

        if existing_username:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Username already taken",
            )

        # ----------------------------------------------------
        # 3. Hash password
        # ----------------------------------------------------

        password_hash = hash_password(
            data.password
        )

        # ----------------------------------------------------
        # 4. Create user document
        # ----------------------------------------------------

        user = {
            "username": data.username,
            "email": data.email,
            "password_hash": password_hash,
            "role": data.role,
            "created_at": datetime.now(timezone.utc),
        }

        # ----------------------------------------------------
        # 5. Insert user
        # ----------------------------------------------------

        result = users_collection.insert_one(user)

        return {
            "message": "Account created successfully",
            "user_id": str(result.inserted_id),
            "role": data.role,
        }

    except HTTPException:
        raise

    except DuplicateKeyError:

        # Database unique indexes handle concurrent signup
        # attempts safely.

        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email or username already registered",
        )

    except PyMongoError:

        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database service unavailable",
        )


# ============================================================
# LOGIN
# ============================================================

@router.post("/login")
def login(data: LoginRequest):

    try:

        # ----------------------------------------------------
        # 1. Find user by email
        # ----------------------------------------------------

        user = users_collection.find_one({
            "email": data.email,
        })

        # ----------------------------------------------------
        # 2. Validate credentials
        # ----------------------------------------------------

        if not user:

            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password",
            )

        password_hash = user.get(
            "password_hash",
            "",
        )

        if not verify_password(
            data.password,
            password_hash,
        ):

            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password",
            )

        # ----------------------------------------------------
        # 3. Validate user role
        # ----------------------------------------------------

        role = user.get("role")

        if role not in {"farmer", "buyer"}:

            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid user account",
            )

        # ----------------------------------------------------
        # 4. Generate JWT
        # ----------------------------------------------------

        token = create_access_token(
            user_id=str(user["_id"]),
            email=user["email"],
            role=role,
        )

        # ----------------------------------------------------
        # 5. Return response
        # ----------------------------------------------------

        return {
            "message": "Login successful",
            "access_token": token,
            "token_type": "bearer",
            "user": {
                "id": str(user["_id"]),
                "username": user["username"],
                "email": user["email"],
                "role": role,
            },
        }

    except HTTPException:
        raise

    except PyMongoError:

        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database service unavailable",
        )
