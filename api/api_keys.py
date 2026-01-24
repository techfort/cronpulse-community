from fastapi import APIRouter, Depends, Form, HTTPException, status
from api.dependencies import get_user_service, get_current_user
from api.models import ApiKeyResponse
from api.services.user_service import UserService, UserServiceException
from db.models.user import User

router = APIRouter()


@router.get("/api-keys", response_model=list[ApiKeyResponse])
def list_api_keys(
    current_user: User = Depends(get_current_user),
    user_service: UserService = Depends(get_user_service),
):
    api_keys = user_service.list_api_keys(current_user.id)
    return [
        ApiKeyResponse(id=api_key.id, name=api_key.name, created_at=api_key.created_at)
        for api_key in api_keys
    ]


@router.post("/api-keys", response_model=ApiKeyResponse)
def create_api_key(
    name: str = Form(...),
    current_user: User = Depends(get_current_user),
    user_service: UserService = Depends(get_user_service),
):
    try:
        api_key = user_service.create_api_key(current_user.id, name)
        return ApiKeyResponse(
            id=api_key.id, name=api_key.name, created_at=api_key.created_at
        )
    except UserServiceException as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/api-keys/{api_key_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_api_key(
    api_key_id: int,
    current_user: User = Depends(get_current_user),
    user_service: UserService = Depends(get_user_service),
):
    try:
        user_service.delete_api_key(api_key_id, current_user.id)
    except UserServiceException as e:
        raise HTTPException(status_code=400, detail=str(e))
