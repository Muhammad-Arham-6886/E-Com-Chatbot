import enum
import uuid
from datetime import datetime
from typing import Optional, TYPE_CHECKING
from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.organization import Organization


class SubscriptionTierEnum(str, enum.Enum):
    FREE = "FREE"
    STARTER = "STARTER"
    GROWTH = "GROWTH"
    ENTERPRISE = "ENTERPRISE"


class SubscriptionStatusEnum(str, enum.Enum):
    ACTIVE = "ACTIVE"
    TRIALING = "TRIALING"
    PAST_DUE = "PAST_DUE"
    CANCELLED = "CANCELLED"


class OrganizationSubscription(Base, TimestampMixin):
    __tablename__ = "organization_subscriptions"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
        index=True,
    )
    organization_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
        index=True,
    )
    tier: Mapped[SubscriptionTierEnum] = mapped_column(
        Enum(SubscriptionTierEnum, name="subscription_tier_enum", native_enum=False),
        default=SubscriptionTierEnum.FREE,
        nullable=False,
    )
    status: Mapped[SubscriptionStatusEnum] = mapped_column(
        Enum(SubscriptionStatusEnum, name="subscription_status_enum", native_enum=False),
        default=SubscriptionStatusEnum.ACTIVE,
        nullable=False,
    )
    current_period_start: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    current_period_end: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    cancel_at_period_end: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )

    # Relationships
    organization: Mapped["Organization"] = relationship("Organization")


class OrganizationUsage(Base, TimestampMixin):
    __tablename__ = "organization_usage"
    __table_args__ = (
        UniqueConstraint("organization_id", "billing_period", name="uq_org_billing_period"),
    )

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
        index=True,
    )
    organization_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    billing_period: Mapped[str] = mapped_column(
        String(7),  # e.g. "2026-08"
        nullable=False,
        index=True,
    )
    chat_messages_count: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )
    crawl_pages_count: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )
    vector_chunks_count: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )
    tokens_consumed: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )
    last_reset_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # Relationships
    organization: Mapped["Organization"] = relationship("Organization")
