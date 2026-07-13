"""
Sanaie Platform — Auth Routes
Registration, login, and token refresh.
"""
from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from slowapi import Limiter
from slowapi.util import get_remote_address

from app.core.database import get_db
from app.core.security import create_access_token, create_refresh_token, verify_token
from app.models.user import User
from app.enums import UserRole
from app.schemas.user import UserCreate, UserResponse
from app.services.user_service import UserService
from app.api.deps import get_current_user, handle_service_exception
from app.core.exceptions import SanaieException

router = APIRouter()
limiter = Limiter(key_func=get_remote_address)


# ==========================================
# Endpoints
# ==========================================

@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user (Client or Worker)",
)
@limiter.limit("10/minute")
def register(request: Request, user_data: UserCreate, db: Session = Depends(get_db)):
    """
    Register a new user with the Sanaie platform.

    - **role**: `client`, `worker`, or `admin`
    - Workers can optionally include `skills` and `latitude`/`longitude`
    - Password must contain uppercase, lowercase, digit, and special character
    """
    try:
        user = UserService.create_user(db, user_data)
        return user
    except SanaieException as e:
        handle_service_exception(e)


@router.post(
    "/login",
    summary="Login and get JWT tokens",
)
@limiter.limit("10/minute")
def login(
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):
    """
    OAuth2 password login.

    - **username**: Email address
    - **password**: User password
    - Returns: `access_token`, `refresh_token`, and `token_type`
    """
    user = UserService.authenticate(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token_data = {
        "sub": user.user_id,
        "role": user.role.value if hasattr(user.role, 'value') else user.role,
    }
    access_token = create_access_token(data=token_data)
    refresh_token = create_refresh_token(data=token_data)

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "user_id": user.user_id,
        "name": user.name,
        "email": user.email,
        "phone_number": user.phone_number,
        "role": user.role.value if hasattr(user.role, 'value') else user.role,
    }


@router.post(
    "/refresh",
    summary="Refresh access token",
)
@limiter.limit("20/minute")
def refresh_token(
    request: Request,
    refresh_token: str,
    db: Session = Depends(get_db),
):
    """
    Exchange a valid refresh token for a new access token.
    """
    payload = verify_token(refresh_token, expected_type="refresh")
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token",
        )

    user_id = payload.get("sub")
    user = UserService.get_by_id(db, user_id)
    if not user:
        raise HTTPException(status_code=401, detail="User not found")

    token_data = {
        "sub": user.user_id,
        "role": user.role.value if hasattr(user.role, 'value') else user.role,
    }
    new_access_token = create_access_token(data=token_data)

    return {
        "access_token": new_access_token,
        "token_type": "bearer",
    }
