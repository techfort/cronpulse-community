from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.security import OAuth2PasswordRequestForm
from api.models import UserResponse
from api.dependencies import get_user_service
from api.services.user_service import UserService, UserServiceException
from slowapi import Limiter
from slowapi.util import get_remote_address

router = APIRouter()
limiter = Limiter(key_func=get_remote_address)


@router.post("/signup", response_model=UserResponse)
@limiter.limit("5/hour")  # Strict limit for signup
def signup(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
    user_service: UserService = Depends(get_user_service),
):
    try:
        user = user_service.signup(email, password)
        return UserResponse(id=user.id, email=user.email)
    except UserServiceException as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/login")
@limiter.limit("10/minute")  # Prevent brute force
def login(
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends(),
    user_service: UserService = Depends(get_user_service),
):
    try:
        token = user_service.login(form_data.username, form_data.password)
        return {"access_token": token, "token_type": "bearer"}
    except UserServiceException as e:
        raise HTTPException(status_code=400, detail=str(e))
