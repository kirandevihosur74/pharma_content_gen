"""Asset listing and file serving."""

import json
import logging
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session as DBSession

from database import get_db, ApprovedAsset

logger = logging.getLogger(__name__)
router = APIRouter()

ASSETS_DIR = Path(__file__).resolve().parent.parent.parent / "approved_library" / "assets"
CONTENT_TYPES = {
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".svg": "image/svg+xml",
    ".gif": "image/gif",
    ".webp": "image/webp",
}


@router.get("/assets")
def list_assets(db: DBSession = Depends(get_db)):
    """List approved assets for UI picker."""
    assets = db.query(ApprovedAsset).order_by(ApprovedAsset.asset_id).all()
    return {
        "assets": [
            {
                "asset_id": a.asset_id,
                "filename": a.filename,
                "source_doc": a.source_doc,
                "source_page": a.source_page,
                "tags": json.loads(a.tags) if a.tags else [],
            }
            for a in assets
        ]
    }


@router.get("/assets/{asset_id}")
def get_asset(asset_id: str, db: DBSession = Depends(get_db)):
    """Serve approved asset file by asset_id."""
    a = db.query(ApprovedAsset).filter(ApprovedAsset.asset_id == asset_id).first()
    if not a:
        logger.warning("[assets] Not found: %s", asset_id)
        raise HTTPException(404, "Asset not found")
    path = ASSETS_DIR / a.filename
    if not path.exists():
        logger.warning("[assets] File missing: %s", path)
        raise HTTPException(404, "Asset file not found")
    ct = CONTENT_TYPES.get(path.suffix.lower(), "application/octet-stream")
    return FileResponse(path, media_type=ct)
