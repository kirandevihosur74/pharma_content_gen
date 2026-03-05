"""Ingestion endpoint."""

import logging

from fastapi import APIRouter, HTTPException

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/ingest")
def run_ingestion():
    """Ingest PDFs and approved assets from approved_library/ into vector DB + SQLite."""
    logger.info("[ingest] Starting ingestion from approved_library/")
    try:
        from ingestion import run_ingestion as do_ingest, ingest_approved_assets

        result = do_ingest()
        asset_result = ingest_approved_assets()
        result["assets_ingested"] = asset_result["ingested"]
        result["assets_updated"] = asset_result["updated"]
        logger.info(
            "[ingest] Complete: %d claims, %d visual_assets, %d approved_assets ingested, %d errors",
            result["claims_added"], result["assets_added"], asset_result["ingested"], len(result["errors"]),
        )
        return result
    except Exception as e:
        logger.exception("[ingest] Failed: %s", e)
        raise HTTPException(500, str(e))
