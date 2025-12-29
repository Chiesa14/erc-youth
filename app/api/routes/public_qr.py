from io import BytesIO

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.db.session import get_db
import app.controllers.activity_checkin as crud_checkin


router = APIRouter(tags=["Public QR"])


@router.get("/checkin-qr/{token}")
def get_checkin_qr_png(token: str, db: Session = Depends(get_db)):
    session = crud_checkin.get_checkin_session_by_token(db, token)
    if not session or session.is_active is False:
        raise HTTPException(status_code=404, detail="Invalid or inactive check-in token")

    try:
        import qrcode
    except Exception:
        raise HTTPException(status_code=500, detail="QR code generator not installed")

    url = crud_checkin.build_checkin_url(token)

    try:
        qr = qrcode.QRCode(
            version=None,
            error_correction=qrcode.constants.ERROR_CORRECT_M,
            box_size=10,
            border=4,
        )
        qr.add_data(url)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")
        img = img.convert("RGB")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate QR code: {e}")

    buf = BytesIO()
    try:
        img.save(buf, format="PNG")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to encode QR PNG: {e}")
    buf.seek(0)

    return StreamingResponse(
        buf,
        media_type="image/png",
        headers={"Cache-Control": "no-store"},
    )
