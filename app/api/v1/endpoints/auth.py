from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_active_user
from app.models.user import User
from app.schemas.user import LoginRequest, Token, UserCreate
from app.services.auth_service import AuthService

router = APIRouter()


@router.post("/login", response_model=Token)
def login(
    login_data: LoginRequest,
    db: Session = Depends(get_db)
):
    auth_service = AuthService(db)
    result = auth_service.login(login_data)
    
    return {
        "access_token": result["access_token"],
        "token_type": result["token_type"]
    }


@router.post("/register")
def register(
    user_data: UserCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_active_user)
):
    if current_user.role.value != "staff":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only staff can create new users"
        )
    
    auth_service = AuthService(db)
    new_user = auth_service.create_user(user_data)
    
    return {"message": "User created successfully", "user_id": new_user.id}


@router.get("/me")
def get_current_user_info(current_user: User = Depends(get_active_user)):
    return {
        "id": current_user.id,
        "username": current_user.username,
        "email": current_user.email,
        "role": current_user.role.value,
        "is_active": current_user.is_active
    }