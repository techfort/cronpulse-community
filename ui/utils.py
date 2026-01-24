from fastapi import Request, status
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from functools import wraps
from typing import Callable, Any
import logging

# Set up Jinja2Templates (adjust the directory if needed)
templates = Jinja2Templates(directory="templates")


def render_template(
    request: Request, template_name: str, context: dict = None, status_code: int = 200
):
    """
    Renders a Jinja2 template with the given context.
    """
    if context is None:
        context = {}
    context["request"] = request
    return templates.TemplateResponse(template_name, context, status_code=status_code)


def require_auth(func: Callable) -> Callable:
    """
    Decorator to ensure the user is authenticated.
    Redirects to login if not authenticated.
    """

    @wraps(func)
    async def wrapper(*args, **kwargs) -> Any:
        kwargs.get("request") or (args[0] if args else None)
        current_user = kwargs.get("current_user")
        if not current_user:
            # Not authenticated, redirect to login
            logging.warning("User not authenticated, redirecting to login.")
            return RedirectResponse(
                url="/login/ui?message=Your session has expired",
                status_code=status.HTTP_302_FOUND,
            )
        return await func(*args, **kwargs)

    return wrapper
