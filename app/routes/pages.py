"""Page CRUD routes."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import Page
from app.schemas import PageCreate, PageMove, PageResponse, PageTreeResponse, PageUpdate

router = APIRouter(prefix="/api/pages", tags=["pages"])


def build_page_tree(
    pages: list[Page], parent_id: str | None = None
) -> list[PageTreeResponse]:
    """Recursively build the page tree from a flat list of Page objects."""
    result: list[PageTreeResponse] = []
    for page in pages:
        if page.parent_page_id == parent_id:
            node = PageTreeResponse.model_construct(
                id=page.id,
                title=page.title,
                icon=page.icon,
                parent_page_id=page.parent_page_id,
            )
            node.children = build_page_tree(pages, page.id)
            result.append(node)
    return result


@router.get("/tree", response_model=list[PageTreeResponse])
async def get_page_tree(db: AsyncSession = Depends(get_db)):
    """Return the full page tree for the sidebar."""
    result = await db.execute(select(Page).order_by(Page.position, Page.created_at))
    pages = list(result.scalars().all())
    return build_page_tree(pages, None)


@router.get("/{page_id}", response_model=PageResponse)
async def get_page(page_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Page).where(Page.id == page_id))
    page = result.scalar_one_or_none()
    if not page:
        raise HTTPException(404, "页面不存在")
    return page


@router.post("", response_model=PageResponse, status_code=201)
async def create_page(data: PageCreate, db: AsyncSession = Depends(get_db)):
    page = Page(**data.model_dump())
    db.add(page)
    await db.commit()
    await db.refresh(page)
    return page


@router.put("/{page_id}", response_model=PageResponse)
async def update_page(
    page_id: str, data: PageUpdate, db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(Page).where(Page.id == page_id))
    page = result.scalar_one_or_none()
    if not page:
        raise HTTPException(404, "页面不存在")
    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(page, key, value)
    await db.commit()
    await db.refresh(page)
    return page


@router.delete("/{page_id}", status_code=204)
async def delete_page(page_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Page).where(Page.id == page_id))
    page = result.scalar_one_or_none()
    if not page:
        raise HTTPException(404, "页面不存在")
    await db.delete(page)
    await db.commit()


@router.put("/{page_id}/move", response_model=PageResponse)
async def move_page(
    page_id: str, data: PageMove, db: AsyncSession = Depends(get_db)
):
    """Move a page to a new parent and/or position in the tree."""
    page = await db.get(Page, page_id)
    if not page:
        raise HTTPException(404, "页面不存在")

    # Prevent circular reference
    if data.parent_page_id:
        if data.parent_page_id == page_id:
            raise HTTPException(400, "不能将页面移动到自身下")
        # Check that target is not a descendant
        async def get_descendants(pid: str) -> set[str]:
            result = await db.execute(
                select(Page.id).where(Page.parent_page_id == pid)
            )
            children = {r[0] for r in result}
            descendants = set(children)
            for cid in children:
                descendants |= await get_descendants(cid)
            return descendants

        descendants = await get_descendants(page_id)
        if data.parent_page_id in descendants:
            raise HTTPException(400, "不能将页面移动到其子页面下")

    page.parent_page_id = data.parent_page_id
    page.position = data.position
    await db.commit()
    await db.refresh(page)
    return page
