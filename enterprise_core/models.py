"""SQLAlchemy persistence models for the first commercial-core slice.

These models do not provide authentication. Callers must obtain tenant_id from
an authenticated server-side identity context, never from an untrusted client.
"""
from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import DateTime, ForeignKeyConstraint, Integer, String, Text, UniqueConstraint, event
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


def utc_now():
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    pass


class InvestigationCase(Base):
    __tablename__ = "investigation_cases"
    __table_args__ = (UniqueConstraint("tenant_id", "id", name="uq_investigation_cases_tenant_id"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    tenant_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(160), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    status: Mapped[str] = mapped_column(String(24), nullable=False, default="open", index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

    __mapper_args__ = {"version_id_col": version}


class AuditEvent(Base):
    __tablename__ = "audit_events"
    __table_args__ = (ForeignKeyConstraint(["tenant_id", "object_id"], ["investigation_cases.tenant_id", "investigation_cases.id"], name="fk_audit_case_tenant"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    tenant_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    actor_id: Mapped[str] = mapped_column(String(128), nullable=False)
    event_type: Mapped[str] = mapped_column(String(64), nullable=False)
    object_type: Mapped[str] = mapped_column(String(64), nullable=False)
    object_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utc_now)
    details_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")


@event.listens_for(AuditEvent, "before_update")
def _reject_audit_update(mapper, connection, target):
    raise ValueError("Audit events are append-only through the ORM.")


@event.listens_for(AuditEvent, "before_delete")
def _reject_audit_delete(mapper, connection, target):
    raise ValueError("Audit events cannot be deleted through the ORM.")
