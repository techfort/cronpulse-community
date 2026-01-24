from fastapi import APIRouter, Request, Depends, Form, status
from fastapi.responses import HTMLResponse, RedirectResponse
from api.services.user_service import UserService, UserServiceException
from api.dependencies import get_user_service, get_current_user
from db.models.user import User
from .utils import render_template, require_auth

router = APIRouter()


@router.get("/api-keys/ui", response_class=HTMLResponse)
@require_auth
async def api_keys_ui(
    request: Request,
    current_user: User = Depends(get_current_user),
    user_service: UserService = Depends(get_user_service),
):
    api_keys = user_service.list_api_keys(current_user.id)
    return render_template(
        request,
        "api_keys.html",
        {"current_user": current_user, "api_keys": api_keys},
    )


@router.post("/api-keys/ui", response_class=HTMLResponse)
@require_auth
async def create_api_key_ui(
    request: Request,
    name: str = Form(...),
    current_user: User = Depends(get_current_user),
    user_service: UserService = Depends(get_user_service),
):
    try:
        user_service.create_api_key(current_user.id, name)

        is_htmx = request.headers.get("HX-Request", "").lower() == "true"
        if is_htmx:
            api_keys = user_service.list_api_keys(current_user.id)
            return render_template(
                request,
                "partials/api_key_list.html",
                {"current_user": current_user, "api_keys": api_keys},
            )

        return RedirectResponse(
            url="/api-keys/ui", status_code=status.HTTP_303_SEE_OTHER
        )
    except UserServiceException as e:
        api_keys = user_service.list_api_keys(current_user.id)
        return render_template(
            request,
            "api_keys.html",
            {
                "current_user": current_user,
                "api_keys": api_keys,
                "error": str(e),
            },
        )


@router.post("/api-keys/{api_key_id}/delete/ui", response_class=HTMLResponse)
@require_auth
async def delete_api_key_ui(
    request: Request,
    api_key_id: int,
    current_user: User = Depends(get_current_user),
    user_service: UserService = Depends(get_user_service),
):
    try:
        user_service.delete_api_key(api_key_id, current_user.id)

        is_htmx = request.headers.get("HX-Request", "").lower() == "true"
        if is_htmx:
            api_keys = user_service.list_api_keys(current_user.id)
            return render_template(
                request,
                "partials/api_key_list.html",
                {"current_user": current_user, "api_keys": api_keys},
            )

        return RedirectResponse(
            url="/api-keys/ui", status_code=status.HTTP_303_SEE_OTHER
        )
    except UserServiceException as e:
        api_keys = user_service.list_api_keys(current_user.id)
        return render_template(
            request,
            "api_keys.html",
            {
                "current_user": current_user,
                "api_keys": api_keys,
                "error": str(e),
            },
        )
