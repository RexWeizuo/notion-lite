"""Block CRUD routes."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import Block, Page
from app.schemas import (
    BatchPositionUpdate,
    BlockCreate,
    BlockResponse,
    BlockUpdate,
)

router = APIRouter(prefix="/api/pages/{page_id}/blocks", tags=["blocks"])


@router.get("", response_model=list[BlockResponse])
async def get_blocks(page_id: str, db: AsyncSession = Depends(get_db)):
    """Get all top-level blocks for a page, ordered by position."""
    result = await db.execute(
        select(Block)
        .where(Block.page_id == page_id, Block.parent_block_id.is_(None))
        .order_by(Block.position)
    )
    return list(result.scalars().all())


@router.post("", response_model=BlockResponse, status_code=201)
async def create_block(
    page_id: str, data: BlockCreate, db: AsyncSession = Depends(get_db)
):
    page_exists = await db.get(Page, page_id)
    if not page_exists:
        raise HTTPException(404, "页面不存在")

    if data.position is None:
        max_pos = await db.execute(
            select(func.max(Block.position)).where(
                Block.page_id == page_id,
                Block.parent_block_id == data.parent_block_id,
            )
        )
        max_val = max_pos.scalar()
        position = (max_val or 0) + 1
    else:
        position = data.position

    block = Block(
        page_id=page_id,
        type=data.type,
        content=data.content,
        parent_block_id=data.parent_block_id,
        position=position,
    )
    db.add(block)
    await db.commit()
    await db.refresh(block)
    return block


@router.put("/{block_id}", response_model=BlockResponse)
async def update_block(
    page_id: str, block_id: str, data: BlockUpdate, db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(Block).where(Block.id == block_id, Block.page_id == page_id)
    )
    block = result.scalar_one_or_none()
    if not block:
        raise HTTPException(404, "块不存在")
    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(block, key, value)
    await db.commit()
    await db.refresh(block)
    return block


@router.delete("/{block_id}", status_code=204)
async def delete_block(
    page_id: str, block_id: str, db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(Block).where(Block.id == block_id, Block.page_id == page_id)
    )
    block = result.scalar_one_or_none()
    if not block:
        raise HTTPException(404, "块不存在")
    await db.delete(block)
    await db.commit()


@router.put("/reorder", response_model=list[BlockResponse])
async def reorder_blocks(
    page_id: str, data: BatchPositionUpdate, db: AsyncSession = Depends(get_db)
):
    """Batch update positions after drag-and-drop reorder."""
    for item in data.updates:
        block = await db.get(Block, item["id"])
        if block and block.page_id == page_id:
            block.position = item["position"]
    await db.commit()
    result = await db.execute(
        select(Block).where(Block.page_id == page_id).order_by(Block.position)
    )
    return list(result.scalars().all())
