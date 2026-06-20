from fastapi import APIRouter
from fastapi.responses import HTMLResponse

from app.email.digest import build_and_send_digest

router = APIRouter()


@router.post("/digest/{profile_id}")
async def send_digest(profile_id: int):
    return await build_and_send_digest(profile_id)


@router.get("/digest/{profile_id}/preview", response_class=HTMLResponse)
async def preview_digest(profile_id: int):
    result = await build_and_send_digest(profile_id)
    return result.get("preview_html") or "<p>Email sent — no preview saved.</p>"
