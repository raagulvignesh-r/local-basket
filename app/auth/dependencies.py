from uuid import UUID

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.auth.jwt import decode_access_token
from app.catalog.store_product_models import StoreProduct
from app.database.session import get_db
from app.stores.models import Store
from app.users.models import User, UserRole


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


def get_current_user(
    token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)
) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = decode_access_token(token)
        user_id = UUID(payload["sub"])
    except (jwt.PyJWTError, KeyError, TypeError, ValueError):
        raise credentials_exception from None

    user = db.get(User, user_id)
    if user is None or not user.is_active:
        raise credentials_exception

    if payload.get("role") != user.role.value:
        raise credentials_exception

    return user


def require_role(required_role: UserRole):
    def role_guard(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role != required_role:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions",
            )
        return current_user

    return role_guard


def require_store_access(
    store_id: UUID, current_user: User = Depends(get_current_user)
) -> User:
    if current_user.role == UserRole.admin:
        return current_user

    if (
        current_user.role == UserRole.employee
        and current_user.store_id == store_id
    ):
        return current_user

    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Insufficient store permissions",
    )


def require_store_product_access(
    store_product_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> User:
    store_product = db.get(StoreProduct, store_product_id)
    if store_product is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Store product not found",
        )

    if current_user.role == UserRole.admin:
        return current_user

    if (
        current_user.role == UserRole.employee
        and current_user.store_id == store_product.store_id
    ):
        return current_user

    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Insufficient store permissions",
    )
