import json
import uuid
from datetime import datetime
from typing import Optional, TYPE_CHECKING
from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.website import Website
    from app.models.organization import Organization


class CommerceIntegration(Base, TimestampMixin):
    __tablename__ = "commerce_integrations"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
        index=True,
    )
    website_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("websites.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
        index=True,
    )
    organization_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    platform: Mapped[str] = mapped_column(
        String(32),
        default="WOOCOMMERCE",  # "WOOCOMMERCE", "SHOPIFY", "CUSTOM"
        nullable=False,
    )
    api_url: Mapped[str] = mapped_column(
        String(512),
        nullable=False,
    )
    consumer_key: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    consumer_secret: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )
    last_sync_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    metadata_json: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )

    # Relationships
    website: Mapped["Website"] = relationship("Website")
    organization: Mapped["Organization"] = relationship("Organization")
