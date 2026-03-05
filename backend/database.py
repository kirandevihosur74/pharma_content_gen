import uuid
import logging
from datetime import datetime, timezone
from sqlalchemy import create_engine, Column, String, Text, DateTime, ForeignKey, Integer, JSON, event, text
from sqlalchemy.orm import sessionmaker, declarative_base

logger = logging.getLogger(__name__)

DATABASE_URL = "sqlite:///./pharma_marketing.db"

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

@event.listens_for(engine, "connect")
def _on_connect(dbapi_conn, connection_record):
    logger.info("DB connection opened (SQLite: %s)", DATABASE_URL)


def new_uuid() -> str:
    return str(uuid.uuid4())


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Session(Base):
    __tablename__ = "sessions"
    id = Column(String, primary_key=True, default=new_uuid)
    content_type = Column(Text, nullable=False, default="email")
    audience = Column(String, nullable=False, default="hcp")
    campaign_goal = Column(String, nullable=False, default="awareness")
    tone = Column(String, nullable=False, default="clinical")
    created_at = Column(DateTime, default=utcnow)


class Message(Base):
    __tablename__ = "messages"
    id = Column(String, primary_key=True, default=new_uuid)
    session_id = Column(String, ForeignKey("sessions.id"), nullable=False)
    role = Column(String, nullable=False)
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, default=utcnow)


class Claim(Base):
    __tablename__ = "claims"
    id = Column(String, primary_key=True, default=new_uuid)
    claim_id = Column(String, nullable=True, unique=True)  # stable slug for deterministic matching
    text = Column(Text, nullable=False)
    verbatim_text = Column(Text, nullable=True)  # canonical exact text; equals text if set
    text_sha256 = Column(String, nullable=True)  # sha256(verbatim_text)
    citation = Column(Text, nullable=False)
    source = Column(String, nullable=False, default="clinical_literature")
    source_doc = Column(String, nullable=True)
    category = Column(String, nullable=False, default="efficacy")
    compliance_status = Column(String, nullable=False, default="approved")
    approved_date = Column(String, nullable=True)
    created_at = Column(DateTime, default=utcnow)


class VisualAsset(Base):
    __tablename__ = "visual_assets"
    id = Column(String, primary_key=True, default=new_uuid)
    asset_type = Column(String, nullable=False)  # "logo" | "image" | "icon" | "color" | "guideline"
    description = Column(Text, nullable=False)
    source_pdf = Column(String, nullable=False)
    page_ref = Column(String, nullable=True)
    metadata_json = Column(Text, nullable=True)  # JSON: colors, dimensions, usage_rules, etc.
    created_at = Column(DateTime, default=utcnow)


class ApprovedAsset(Base):
    """Approved visual assets from approved_library/assets/ — enforced for compliance."""
    __tablename__ = "approved_assets"
    asset_id = Column(String, primary_key=True)
    filename = Column(String, nullable=False)
    sha256 = Column(String, nullable=False)
    source_doc = Column(String, nullable=False, default="STYLE_GUIDE")
    source_page = Column(String, nullable=True)
    tags = Column(Text, nullable=True)  # JSON array of tags
    created_at = Column(DateTime, default=utcnow)


class Version(Base):
    __tablename__ = "versions"
    id = Column(String, primary_key=True, default=new_uuid)
    session_id = Column(String, ForeignKey("sessions.id"), nullable=False)
    html = Column(Text, nullable=False)
    content_type = Column(String, nullable=False, default="email")
    revision_number = Column(Integer, nullable=False, default=1)
    claim_ids_used = Column(Text, nullable=True)
    asset_ids_used = Column(Text, nullable=True)
    created_at = Column(DateTime, default=utcnow)


# Approved claims are loaded from approved_library/ (PDFs: FRUZAQLA Style Guide, fruzaqla-prescribing-information).
# Add an ingestion script or API to parse PDFs and populate the claims table.


def init_db():
    logger.info("Initializing database — creating tables if needed")
    Base.metadata.create_all(bind=engine)
    _migrate_add_columns()


def _migrate_add_columns():
    """Add new columns to existing tables if missing (SQLite)."""
    migrations = [
        ("claims", "claim_id", "VARCHAR"),
        ("claims", "verbatim_text", "TEXT"),
        ("claims", "text_sha256", "VARCHAR"),
        ("claims", "source_doc", "VARCHAR"),
        ("versions", "asset_ids_used", "TEXT"),
    ]
    for table, col, col_type in migrations:
        try:
            with engine.connect() as conn:
                conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {col} {col_type}"))
                conn.commit()
            logger.info("Migration: added %s.%s", table, col)
        except Exception:
            pass  # column likely exists


def get_db():
    db = SessionLocal()
    logger.debug("DB session opened")
    try:
        yield db
    finally:
        db.close()
        logger.debug("DB session closed")
