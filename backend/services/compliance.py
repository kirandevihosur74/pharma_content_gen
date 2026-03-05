"""Compliance validation: parse HTML, validate claims/assets, image sources."""

import re
import html as html_mod

from schemas import ReviewItem
from database import Claim


def parse_html_compliance(html: str) -> tuple[list[str], dict[str, str], list[str]]:
    """Extract claim_ids, claim_id->text, asset_ids from HTML."""
    claim_ids: list[str] = []
    claim_texts: dict[str, str] = {}
    asset_ids: list[str] = []
    if not html:
        return claim_ids, claim_texts, asset_ids
    for m in re.finditer(r'data-claim-id=["\']([^"\']+)["\']', html):
        claim_ids.append(m.group(1))
    for tag in ("li", "span", "p"):
        for m in re.finditer(
            rf'<{tag}[^>]*data-claim-id=["\']([^"\']+)["\'][^>]*>([\s\S]*?)</{tag}>',
            html,
        ):
            cid, inner = m.group(1), m.group(2)
            text = re.sub(r"<[^>]+>", "", inner).strip().replace("&nbsp;", " ").replace("\xa0", " ")
            if cid and text and cid not in claim_texts:
                claim_texts[cid] = text
    for m in re.finditer(r'data-claim-id=["\']([^"\']+)["\'][^>]*>([^<]+)', html):
        cid, text = m.group(1), m.group(2).strip()
        if cid and text and cid not in claim_texts:
            claim_texts[cid] = text
    for m in re.finditer(r'data-asset-id=["\']([^"\']+)["\']', html):
        asset_ids.append(m.group(1))
    return claim_ids, claim_texts, asset_ids


def _normalize_text(s: str) -> str:
    """Normalize for comparison: collapse whitespace, unescape HTML entities."""
    t = html_mod.unescape(s).strip()
    return " ".join(t.split())


def validate_claims_exact(
    html_claim_ids: list[str],
    html_claim_texts: dict[str, str],
    approved_map: dict[str, Claim],
) -> ReviewItem:
    """Verify every claim_id exists and rendered text equals verbatim exactly."""
    missing = []
    mismatch = []
    for cid in html_claim_ids:
        c = approved_map.get(cid)
        if not c:
            missing.append(cid)
            continue
        verbatim = _normalize_text(c.verbatim_text or c.text)
        rendered = _normalize_text(html_claim_texts.get(cid, ""))
        if rendered != verbatim:
            mismatch.append(f"{cid[:12]}...")
    if missing:
        return ReviewItem(
            check="Claim Exact Match",
            status="fail",
            detail=f"Unknown claim IDs in content: {missing[:5]}. All claims must be from approved library.",
        )
    if mismatch:
        return ReviewItem(
            check="Claim Exact Match",
            status="fail",
            detail=f"Claim text mismatch (not verbatim): {mismatch[:3]}. Claims must match approved text exactly.",
        )
    if not html_claim_ids:
        return ReviewItem(
            check="Claim Exact Match",
            status="fail",
            detail="No claims with data-claim-id found in content.",
        )
    return ReviewItem(
        check="Claim Exact Match",
        status="pass",
        detail=f"All {len(html_claim_ids)} claims match approved library verbatim.",
    )


def validate_assets(html_asset_ids: list[str], approved_ids: set[str]) -> ReviewItem:
    """Verify every asset_id exists in approved_assets."""
    unknown = [a for a in html_asset_ids if a not in approved_ids]
    if unknown:
        return ReviewItem(
            check="Visual Assets",
            status="fail",
            detail=f"Unauthorized asset IDs: {unknown}. All assets must be from approved library.",
        )
    if html_asset_ids:
        return ReviewItem(
            check="Visual Assets",
            status="pass",
            detail=f"All {len(html_asset_ids)} visual assets match approved library.",
        )
    return ReviewItem(
        check="Visual Assets",
        status="pass",
        detail="No visual assets in content (text-only).",
    )


def validate_img_sources(html: str) -> ReviewItem | None:
    """Fail if any img has external src (http/https/data:) or lacks data-asset-id."""
    if not html:
        return None
    for m in re.finditer(r"<img[^>]*>", html, re.IGNORECASE):
        tag = m.group(0)
        src_m = re.search(r'\ssrc=["\']([^"\']*)["\']', tag, re.IGNORECASE)
        asset_m = re.search(r'\sdata-asset-id=["\']([^"\']+)["\']', tag, re.IGNORECASE)
        src = (src_m.group(1) or "").strip() if src_m else ""
        if src:
            if src.startswith("data:"):
                return ReviewItem(
                    check="Image Sources",
                    status="fail",
                    detail="Images must use approved library URLs only. data: src not allowed.",
                )
            if (src.startswith("http://") or src.startswith("https://")) and "/assets/" not in src:
                return ReviewItem(
                    check="Image Sources",
                    status="fail",
                    detail="Images must use approved library URLs only. External src not allowed.",
                )
        if not asset_m:
            return ReviewItem(
                check="Image Sources",
                status="fail",
                detail="Every <img> must have data-asset-id. Unapproved images are not allowed.",
            )
    return None
