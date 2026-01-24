from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from .utils import render_template

router = APIRouter()


@router.get("/documentation", response_class=HTMLResponse)
async def documentation_ui(request: Request):
    """
    Render the documentation page (templates/documentation.html).
    Public page — no auth required.
    """
    return render_template(request, "documentation.html")
