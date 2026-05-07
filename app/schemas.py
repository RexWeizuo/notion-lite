"""Pydantic request/response schemas."""
from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field


# --- Page Schemas ---

class PageCreate(BaseModel):
    title: str = "无标题"
    icon: Optional[str] = None
    parent_page_id: Optional[str] = None


class PageUpdate(BaseModel):
    title: Optional[str] = None
    icon: Optional[str] = None


class PageResponse(BaseModel):
    id: str
    title: str
    icon: Optional[str] = None
    parent_page_id: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class PageTreeResponse(BaseModel):
    """Page node with nested children for the sidebar tree."""

    id: str
    title: str
    icon: Optional[str] = None
    parent_page_id: Optional[str] = None
    children: list["PageTreeResponse"] = Field(default_factory=list, init=False)

    model_config = {"from_attributes": True}


# --- Block Schemas ---

class BlockCreate(BaseModel):
    type: str = "paragraph"
    content: dict[str, Any] = Field(default_factory=dict)
    parent_block_id: Optional[str] = None
    position: Optional[int] = None


class BlockUpdate(BaseModel):
    type: Optional[str] = None
    content: Optional[dict[str, Any]] = None


class BlockResponse(BaseModel):
    id: str
    page_id: str
    type: str
    content: dict[str, Any]
    parent_block_id: Optional[str] = None
    position: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class BatchPositionUpdate(BaseModel):
    """Batch update block positions after drag-and-drop reorder."""

    updates: list[dict[str, Any]]


# --- Page Move ---


class PageMove(BaseModel):
    """Move a page to a new parent and/or position."""

    parent_page_id: Optional[str] = None
    position: int = 0


# --- Markdown ---


class MarkdownImport(BaseModel):
    markdown: str
    title: str = "导入笔记"
