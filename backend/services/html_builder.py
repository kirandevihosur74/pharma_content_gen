"""HTML generation: inject claims/assets, build templates, sanitize edits."""

import os
import re
import html as html_mod

from database import Claim

BASE_URL = os.environ.get("BASE_URL", "http://localhost:8000")


def inject_claims_and_assets(html: str, claims: list[Claim], asset_ids: list[str]) -> str:
    """Replace {CLAIM:id} and {{CLAIM:id}} with verbatim text + data-claim-id; inject asset img tags."""
    claim_by_id = {(c.claim_id or c.id): (c.verbatim_text or c.text or "") for c in claims}

    def repl(m):
        cid = m.group(1)
        verbatim = claim_by_id.get(cid, "")
        if not verbatim:
            return m.group(0)
        escaped = html_mod.escape(verbatim)
        return f'<span data-claim-id="{cid}">{escaped}</span>'

    html = re.sub(r"\{\{?CLAIM:([^}]+)\}\}?", repl, html)

    asset_block = "".join(
        f'<img src="{BASE_URL}/assets/{aid}" data-asset-id="{aid}" alt="" />'
        for aid in asset_ids
    )
    html = html.replace("{{ASSETS}}", asset_block)
    return html


def sanitize_edit_html(html: str, claims: list[Claim], asset_ids: list[str]) -> str:
    """Re-render claim blocks from IDs so edit cannot alter verbatim text."""
    claim_by_id = {(c.claim_id or c.id): (c.verbatim_text or c.text or "") for c in claims}

    def repl_claim_block(m):
        cid = m.group(2)
        verbatim = claim_by_id.get(cid, "")
        if not verbatim:
            return m.group(0)
        escaped = html_mod.escape(verbatim)
        return f'<span data-claim-id="{cid}">{escaped}</span>'

    html = re.sub(
        r'<(\w+)[^>]*\sdata-claim-id=["\']([^"\']+)["\'][^>]*>[\s\S]*?</\1>',
        repl_claim_block,
        html,
    )
    html = inject_claims_and_assets(html, claims, asset_ids)
    return html


def build_html(claims: list[Claim], content_type: str, asset_ids: list[str] | None = None) -> str:
    asset_ids = asset_ids or []
    if content_type == "banner":
        return _build_banner_html(claims, asset_ids)
    if content_type == "social":
        return _build_social_html(claims, asset_ids)
    return _build_email_html(claims, asset_ids)


def _build_email_html(claims: list[Claim], asset_ids: list[str]) -> str:
    efficacy = [c for c in claims if c.category in ("efficacy", "indication", "mechanism", "quality_of_life", "dosing")]
    safety = [c for c in claims if c.category == "safety"]
    cid = lambda c: c.claim_id or c.id
    vt = lambda c: c.verbatim_text or c.text
    efficacy_items = "\n".join(
        f'        <li class="claim" data-claim-id="{cid(c)}">{html_mod.escape(vt(c))}</li>' for c in efficacy
    )
    safety_items = "\n".join(
        f'        <li data-claim-id="{cid(c)}">{html_mod.escape(vt(c))}</li>' for c in safety
    ) if safety else "        <li>Please see full Prescribing Information for Important Safety Information.</li>"
    all_citations = list(dict.fromkeys(c.citation for c in claims))
    citation_items = "\n".join(f"        <li>{cit}</li>" for cit in all_citations)
    asset_block = "".join(
        f'<img src="{BASE_URL}/assets/{aid}" data-asset-id="{aid}" alt="" style="max-width:100%;" />\n    '
        for aid in asset_ids
    ) if asset_ids else ""
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8" />
<meta name="viewport" content="width=device-width, initial-scale=1.0" />
<title>FRUZAQLA \u2014 HCP Email</title>
<style>
  body {{ font-family: 'Helvetica Neue', Arial, sans-serif; margin: 0; padding: 0; background: #f9f9f9; color: #222; }}
  .container {{ max-width: 640px; margin: 0 auto; background: #fff; }}
  .header {{ background: linear-gradient(135deg, #0f4c75 0%, #1b262c 100%); color: #fff; padding: 36px 28px; }}
  .header h1 {{ margin: 0; font-size: 24px; letter-spacing: 0.5px; }}
  .header .subtitle {{ margin: 6px 0 0; font-size: 14px; opacity: 0.9; font-style: italic; }}
  .header .hcp-only {{ margin: 10px 0 0; font-size: 11px; opacity: 0.7; text-transform: uppercase; letter-spacing: 1px; }}
  .indication {{ background: #f0f4f8; padding: 16px 28px; font-size: 12px; color: #555; border-bottom: 1px solid #e0e0e0; }}
  .section {{ padding: 28px; }}
  .section h2 {{ color: #0f4c75; font-size: 18px; border-bottom: 2px solid #bbe1fa; padding-bottom: 8px; margin-top: 0; }}
  .claim {{ margin-bottom: 14px; line-height: 1.6; font-size: 14px; }}
  .safety {{ background: #fff8f0; border-left: 4px solid #d35400; padding: 20px 28px; }}
  .safety h2 {{ color: #c0392b; font-size: 16px; margin-top: 0; }}
  .safety ul {{ font-size: 13px; line-height: 1.6; }}
  .cta {{ text-align: center; padding: 24px 28px; }}
  .cta a {{ display: inline-block; background: #0f4c75; color: #fff; text-decoration: none; padding: 12px 32px; border-radius: 4px; font-size: 14px; font-weight: 600; }}
  .footer {{ background: #f5f5f5; padding: 24px 28px; font-size: 11px; color: #777; }}
  .footer ol {{ padding-left: 18px; line-height: 1.6; }}
  .footer .legal {{ margin-top: 12px; font-size: 10px; color: #999; }}
</style>
</head>
<body>
  <div class="container">
    {asset_block}
    <div class="header">
      <h1>FRUZAQLA<sup>&reg;</sup></h1>
      <div class="subtitle">fruquintinib | capsules</div>
      <div class="hcp-only">For US healthcare professionals only</div>
    </div>
    <div class="indication">
      <strong>Indication:</strong> FRUZAQLA is indicated for the treatment of adult patients with metastatic colorectal cancer (mCRC) who have been previously treated with fluoropyrimidine-, oxaliplatin-, and irinotecan-based chemotherapy, an anti-VEGF biological therapy, and, if RAS wild-type and medically appropriate, an anti-EGFR therapy.
    </div>
    <div class="section" id="efficacy">
      <h2>Efficacy &amp; Clinical Evidence</h2>
      <ul>
{efficacy_items}
      </ul>
    </div>
    <div class="safety" id="safety">
      <h2>Important Safety Information</h2>
      <ul>
{safety_items}
      </ul>
      <p style="font-size:12px; margin-top:12px;">Please see full <a href="#" style="color:#0f4c75;">Prescribing Information</a>, including BOXED WARNING.</p>
    </div>
    <div class="cta"><a href="#">Learn More at FRUZAQLA-hcp.com</a></div>
    <div class="footer">
      <h3 style="margin-top:0; font-size:12px; color:#555;">References</h3>
      <ol>
{citation_items}
      </ol>
      <div class="legal">FRUZAQLA is a registered trademark. &copy; 2025 Takeda Pharmaceutical Company Limited.<br/>All rights reserved. US-FRZ-2500001 03/2025</div>
    </div>
  </div>
</body>
</html>"""


def _build_banner_html(claims: list[Claim], asset_ids: list[str]) -> str:
    cid = lambda c: c.claim_id or c.id
    vt = lambda c: c.verbatim_text or c.text
    if claims:
        headline = vt(claims[0])
        if len(headline) > 120:
            headline = headline[:117] + "..."
        headline_span = f'<span data-claim-id="{cid(claims[0])}">{html_mod.escape(headline)}</span>'
    else:
        headline_span = "Discover FRUZAQLA"
    return f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="UTF-8" />
<style>body{{margin:0;padding:0;font-family:'Helvetica Neue',Arial,sans-serif}}.banner{{width:728px;height:90px;background:linear-gradient(135deg,#0f4c75,#1b262c);color:#fff;display:flex;align-items:center;padding:0 20px;box-sizing:border-box;overflow:hidden}}.banner .brand{{font-size:18px;font-weight:700;white-space:nowrap;margin-right:16px;min-width:120px}}.banner .msg{{font-size:11px;line-height:1.4;flex:1;opacity:.95}}.banner .cta-btn{{background:#bbe1fa;color:#0f4c75;border:none;padding:8px 16px;border-radius:3px;font-size:11px;font-weight:700;cursor:pointer;white-space:nowrap}}.isi{{font-size:8px;color:#999;padding:4px 20px}}</style>
</head><body>
<div class="banner"><div class="brand">FRUZAQLA<sup>&reg;</sup></div><div class="msg">{headline_span}</div><button class="cta-btn">Learn&nbsp;More</button></div>
<div class="isi">Please see full Prescribing Information, including BOXED WARNING. For US HCPs only. &copy; 2025 Takeda</div>
</body></html>"""


def _build_social_html(claims: list[Claim], asset_ids: list[str]) -> str:
    cid = lambda c: c.claim_id or c.id
    vt = lambda c: c.verbatim_text or c.text
    bullets = "\n".join(
        f'    <li data-claim-id="{cid(c)}">{html_mod.escape(vt(c))}</li>' for c in claims[:3]
    )
    citations = ", ".join(dict.fromkeys(c.citation for c in claims[:3]))
    return f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="UTF-8" />
<style>body{{margin:0;padding:0;font-family:'Helvetica Neue',Arial,sans-serif;background:#f9f9f9}}.card{{max-width:480px;margin:0 auto;background:#fff;border-radius:8px;overflow:hidden;box-shadow:0 2px 12px rgba(0,0,0,.08)}}.card-header{{background:linear-gradient(135deg,#0f4c75,#1b262c);color:#fff;padding:20px 24px}}.card-header h1{{margin:0;font-size:20px}}.card-header p{{margin:4px 0 0;font-size:12px;opacity:.8}}.card-body{{padding:20px 24px}}.card-body ul{{padding-left:18px;font-size:13px;line-height:1.7}}.card-footer{{padding:12px 24px;font-size:9px;color:#999;border-top:1px solid #eee}}</style>
</head><body>
<div class="card"><div class="card-header"><h1>FRUZAQLA<sup>&reg;</sup> (fruquintinib)</h1><p>For US healthcare professionals only</p></div>
<div class="card-body"><ul>
{bullets}
</ul></div>
<div class="card-footer">See full Prescribing Information, including BOXED WARNING. Ref: {citations}. &copy; 2025 Takeda</div></div>
</body></html>"""
