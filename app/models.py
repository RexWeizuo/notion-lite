"""SQLAlchemy ORM models."""
import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import DeclarativeBase, relationship


def gen_id() -> str:
    return uuid.uuid4().hex[:12]


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    pass


class Page(Base):
    __tablename__ = "pages"

    id = Column(String(12), primary_key=True, default=gen_id)
    title = Column(String(500), nullable=False, default="无标题")
    icon = Column(String(10), nullable=True)
    parent_page_id = Column(
        String(12), ForeignKey("pages.id"), nullable=True, index=True
    )
    position = Column(Integer, nullable=False, default=0, index=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=utcnow,
        onupdate=utcnow,
    )

    parent = relationship("Page", remote_side="Page.id", back_populates="children")
    children = relationship(
        "Page", back_populates="parent", cascade="all, delete-orphan"
    )
    blocks = relationship(
        "Block",
        back_populates="page",
        cascade="all, delete-orphan",
        order_by="Block.position",
    )


class Block(Base):
    __tablename__ = "blocks"

    id = Column(String(12), primary_key=True, default=gen_id)
    page_id = Column(
        String(12), ForeignKey("pages.id", ondelete="CASCADE"), nullable=False, index=True
    )
    type = Column(String(30), nullable=False)
    content = Column(JSONB, nullable=False, default=dict)
    parent_block_id = Column(
        String(12), ForeignKey("blocks.id"), nullable=True, index=True
    )
    position = Column(Integer, nullable=False, default=0, index=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=utcnow,
        onupdate=utcnow,
    )

    page = relationship("Page", back_populates="blocks")
    parent_block = relationship(
        "Block", remote_side="Block.id", back_populates="children"
    )
    children = relationship(
        "Block",
        back_populates="parent_block",
        cascade="all, delete-orphan",
        order_by="Block.position",
    )
