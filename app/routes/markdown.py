"""Markdown import/export routes."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.markdown_utils import blocks_to_markdown, markdown_to_blocks
from app.models import Block, Page
from app.schemas import MarkdownImport

router = APIRouter(prefix="/api/pages", tags=["markdown"])


@router.get("/{page_id}/export/markdown")
async def export_markdown(page_id: str, db: AsyncSession = Depends(get_db)):
    """Export a page's blocks as a Markdown string."""
    page = await db.get(Page, page_id)
    if not page:
        raise HTTPException(404, "页面不存在")

    result = await db.execute(
        select(Block)
        .where(Block.page_id == page_id, Block.parent_block_id.is_(None))
        .order_by(Block.position)
    )
    blocks = list(result.scalars().all())
    md = blocks_to_markdown(blocks)
    return {"title": page.title, "markdown": md}


@router.post("/import/markdown", status_code=201)
async def import_markdown(data: MarkdownImport, db: AsyncSession = Depends(get_db)):
    """Create a new page from Markdown text."""
    page = Page(title=data.title)
    db.add(page)
    await db.flush()  # get page.id without full commit

    block_dicts = markdown_to_blocks(data.markdown)
    for i, bd in enumerate(block_dicts):
        block = Block(
            page_id=page.id,
            type=bd["type"],
            content=bd["content"],
            position=i,
        )
        db.add(block)

    await db.commit()
    await db.refresh(page)
    return {"page_id": page.id, "title": page.title, "block_count": len(block_dicts)}
