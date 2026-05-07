"""Spaced repetition vocabulary — two-round review with five-level categorization."""
import json
from datetime import date, timedelta

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db

router = APIRouter(prefix="/api/vocab", tags=["vocab"])

# Category page titles (children of 单词模块)
CATEGORIES = ["还没学习", "一轮掌握", "二轮掌握", "三轮掌握", "太熟悉"]
# Intervals for next review per level
NEXT_INTERVAL = {
    "还没学习": 0,     # review tomorrow (if marked known)
    "一轮掌握": 1,     # tomorrow
    "二轮掌握": 7,     # next week
    "三轮掌握": 30,    # next month
    "太熟悉": None,    # no more review
}


class ReviewResult(BaseModel):
    known: bool = True
    mastered: bool = False
    round: int = 1  # 1 or 2
    user_notes: str = ""
    user_meaning: str = ""


class SettingsUpdate(BaseModel):
    daily_new_words: int = 50


async def _get_cat_ids(db: AsyncSession) -> dict[str, str]:
    """Return {category_title: page_id} for the five folders under 单词模块."""
    rows = await db.execute(text("""
        SELECT p.title, p.id FROM pages p
        JOIN pages vocab ON vocab.id = p.parent_page_id
        JOIN pages p201 ON p201.id = vocab.parent_page_id
        WHERE p201.title = '201' AND vocab.title = '单词模块'
          AND p.title IN ('还没学习','一轮掌握','二轮掌握','三轮掌握','太熟悉')
    """))
    return {r[0]: r[1] for r in rows}


async def _get_config(db: AsyncSession, key: str, default: str = "") -> str:
    r = await db.execute(text("SELECT value FROM app_config WHERE key = :k"), {"k": key})
    row = r.fetchone()
    return row[0] if row else default


async def _set_config(db: AsyncSession, key: str, value: str):
    await db.execute(text(
        "INSERT INTO app_config (key, value, updated_at) VALUES (:k, :v, NOW()) "
        "ON CONFLICT (key) DO UPDATE SET value = :v2, updated_at = NOW()"
    ), {"k": key, "v": value, "v2": value})


@router.get("/stats")
async def get_stats(db: AsyncSession = Depends(get_db)):
    """Return word counts per category."""
    cat_ids = await _get_cat_ids(db)
    stats = {}
    total = 0
    for cat, cid in cat_ids.items():
        r = await db.execute(text(
            "SELECT count(*) FROM pages WHERE parent_page_id = :cid"
        ), {"cid": cid})
        cnt = r.scalar() or 0
        stats[cat] = cnt
        total += cnt

    # Today's due count (words in progress with next_review_date <= today)
    today = date.today()
    r = await db.execute(text(
        "SELECT count(*) FROM word_progress wp "
        "JOIN pages p ON p.id = wp.page_id "
        "JOIN pages cat ON cat.id = p.parent_page_id "
        "WHERE cat.title IN ('一轮掌握','二轮掌握','三轮掌握') "
        "AND wp.next_review_date <= :today AND wp.today_round < 2"
    ), {"today": today})
    due = r.scalar() or 0

    return {
        "categories": stats,
        "total": total,
        "due": due,
    }


@router.get("/daily-tasks")
async def get_daily_tasks(db: AsyncSession = Depends(get_db)):
    """Return today's review queue. Resumes from last position if interrupted."""
    today = date.today()
    cat_ids = await _get_cat_ids(db)
    daily_new = int(await _get_config(db, "daily_new_words", "50"))
    session_key = f"session_{today.isoformat()}"
    session_raw = await _get_config(db, session_key, "{}")
    session = json.loads(session_raw) if session_raw else {}

    current_round = session.get("round", 1)
    completed_ids = set(session.get("completed", []))

    # If session is done (round=0) but user reloads, clear and restart
    if current_round == 0:
        await db.execute(text("DELETE FROM app_config WHERE key = :k"), {"k": session_key})
        await db.commit()
        session = {}
        current_round = 1
        completed_ids = set()

    # --- Round 1: due review words + new words ---
    if current_round == 1:
        if not session.get("word_ids"):
            # Fresh session: build word list
            r = await db.execute(text("""
                SELECT p.id, p.title, wp.review_count, wp.forget_count,
                       wp.user_notes, wp.user_meaning, cat.title as category
                FROM word_progress wp
                JOIN pages p ON p.id = wp.page_id
                JOIN pages cat ON cat.id = p.parent_page_id
                WHERE cat.title IN ('一轮掌握','二轮掌握','三轮掌握')
                  AND wp.next_review_date <= :today
                  AND wp.today_round < 2
                ORDER BY wp.next_review_date ASC
            """), {"today": today})
            review_words = [dict(r._mapping) for r in r]

            r2 = await db.execute(text("""
                SELECT p.id, p.title
                FROM pages p
                WHERE p.parent_page_id = :cid
                  AND p.id NOT IN (SELECT page_id FROM word_progress)
                ORDER BY p.id ASC
                LIMIT :lim
            """), {"cid": cat_ids["还没学习"], "lim": daily_new})
            new_words = [dict(r2._mapping) for r2 in r2]

            words = (
                [{**w, "is_new": False, "category": w.get("category", "还没学习")} for w in review_words] +
                [{**w, "is_new": True, "category": "还没学习"} for w in new_words]
            )
            session["word_ids"] = [w["id"] for w in words]
            session["round"] = 1
            await _set_config(db, session_key, json.dumps(session))
            await db.commit()

        # Return words, skipping completed ones — for resume support
        all_word_ids = session.get("word_ids", [])
        remaining_ids = [wid for wid in all_word_ids if wid not in completed_ids]

        if not remaining_ids:
            # All round 1 words done → move to round 2
            mastered_set = set(session.get("mastered", []))
            round2_ids = [wid for wid in all_word_ids if wid not in mastered_set]
            if round2_ids:
                session["round"] = 2
                session["completed"] = []
                await _set_config(db, session_key, json.dumps(session))
                await db.commit()
                # Fall through to round 2 logic below (recursive call)
                # Instead, just build round 2 words here
                return await _build_round2(db, round2_ids, daily_new, session, session_key)
            else:
                session["round"] = 0
                await _set_config(db, session_key, json.dumps(session))
                await db.commit()
                return {"round": 0, "words": [], "settings": {"daily_new_words": daily_new}, "done": True}

        # Fetch word details for remaining words
        placeholders = ",".join([f"'{wid}'" for wid in remaining_ids])
        r = await db.execute(text(f"""
            SELECT p.id, p.title, COALESCE(wp.review_count,0) as review_count,
                   COALESCE(wp.forget_count,0) as forget_count,
                   COALESCE(wp.user_notes,'') as user_notes,
                   COALESCE(wp.user_meaning,'') as user_meaning,
                   COALESCE(cat.title,'还没学习') as category
            FROM pages p
            LEFT JOIN word_progress wp ON wp.page_id = p.id
            LEFT JOIN pages cat ON cat.id = p.parent_page_id
            WHERE p.id IN ({placeholders})
        """))
        words = []
        seen = set()
        for row in r:
            w = dict(row._mapping)
            wid = w["id"]
            if wid not in seen:
                seen.add(wid)
                is_new = wid not in {rw.get("id") for rw in ([w for w in []] if 'review_words' not in dir() else [])}
                words.append({**w, "is_new": w.get("category") == "还没学习"})

        return {"round": 1, "words": words, "settings": {"daily_new_words": daily_new},
                "resumed": len(completed_ids) > 0}

    # --- Round 2 ---
    else:
        all_word_ids = session.get("word_ids", [])
        mastered_set = set(session.get("mastered", []))
        round2_ids = [wid for wid in all_word_ids if wid not in mastered_set and wid not in completed_ids]

        if not round2_ids:
            session["round"] = 0
            await _set_config(db, session_key, json.dumps(session))
            await db.commit()
            return {"round": 0, "words": [], "settings": {"daily_new_words": daily_new}, "done": True}

        return await _build_round2(db, round2_ids, daily_new, session, session_key)


async def _build_round2(db, round2_ids, daily_new, session, session_key):
    placeholders = ",".join([f"'{wid}'" for wid in round2_ids])
    r = await db.execute(text(f"""
        SELECT p.id, p.title, COALESCE(wp.review_count,0) as review_count,
               COALESCE(wp.forget_count,0) as forget_count,
               COALESCE(wp.user_notes,'') as user_notes,
               COALESCE(wp.user_meaning,'') as user_meaning,
               COALESCE(cat.title,'还没学习') as category
        FROM pages p
        LEFT JOIN word_progress wp ON wp.page_id = p.id
        LEFT JOIN pages cat ON cat.id = p.parent_page_id
        WHERE p.id IN ({placeholders})
    """))
    words = []
    seen = set()
    for row in r:
        w = dict(row._mapping)
        if w["id"] not in seen:
            seen.add(w["id"])
            words.append({**w, "is_new": False})
    return {"round": 2, "words": words, "settings": {"daily_new_words": daily_new}}


@router.post("/{page_id}/review")
async def review_word(
    page_id: str, result: ReviewResult, db: AsyncSession = Depends(get_db)
):
    """Record a review result. Moves page between categories."""
    today = date.today()
    cat_ids = await _get_cat_ids(db)
    session_key = f"session_{today.isoformat()}"
    session_raw = await _get_config(db, session_key, "{}")
    session = json.loads(session_raw) if session_raw else {}

    # Get current page category
    r = await db.execute(text(
        "SELECT p.parent_page_id, cat.title as cat_title FROM pages p "
        "JOIN pages cat ON cat.id = p.parent_page_id WHERE p.id = :pid"
    ), {"pid": page_id})
    row = r.fetchone()
    current_cat = row[1] if row else "还没学习"

    # Get or create progress
    r = await db.execute(text("SELECT * FROM word_progress WHERE page_id = :pid"), {"pid": page_id})
    progress = r.fetchone()
    if not progress:
        await db.execute(text(
            "INSERT INTO word_progress (page_id, status, review_count, forget_count, today_round) "
            "VALUES (:pid, 'new', 0, 0, 0)"
        ), {"pid": page_id})
        review_count = 0
        forget_count = 0
    else:
        review_count = progress.review_count
        forget_count = progress.forget_count

    # Determine new category
    if result.mastered:
        new_cat = "太熟悉"
        next_review = None
        review_count = 99
    elif not result.known:
        new_cat = "还没学习"
        next_review = today + timedelta(days=1)
        review_count = 0
        forget_count += 1
    else:  # known
        # Progress through levels
        level_map = {"还没学习": "一轮掌握", "一轮掌握": "二轮掌握", "二轮掌握": "三轮掌握", "三轮掌握": "太熟悉"}
        new_cat = level_map.get(current_cat, "一轮掌握")
        interval = NEXT_INTERVAL.get(new_cat)
        next_review = today + timedelta(days=interval) if interval else None
        review_count += 1

    # Move page to new category folder
    if new_cat != current_cat and new_cat in cat_ids:
        await db.execute(text(
            "UPDATE pages SET parent_page_id = :cid WHERE id = :pid"
        ), {"cid": cat_ids[new_cat], "pid": page_id})

    # Update progress
    await db.execute(text("""
        UPDATE word_progress
        SET status = :st, review_count = :rc, forget_count = :fc,
            next_review_date = :nrd, last_review_date = :today,
            today_round = :tr, user_notes = :un, user_meaning = :um
        WHERE page_id = :pid
    """), {
        "st": new_cat, "rc": review_count, "fc": forget_count,
        "nrd": next_review, "today": today, "tr": result.round,
        "un": result.user_notes, "um": result.user_meaning,
        "pid": page_id,
    })

    # Track session
    completed = session.get("completed", [])
    if page_id not in completed:
        completed.append(page_id)
    session["completed"] = completed

    if result.mastered:
        mastered = session.get("mastered", [])
        if page_id not in mastered:
            mastered.append(page_id)
        session["mastered"] = mastered

    # Check if round finished
    word_ids = session.get("word_ids", [])
    remaining = [wid for wid in word_ids if wid not in completed]
    if not remaining:
        # Round complete
        if session.get("round", 1) == 1:
            # Start round 2 (remove mastered words)
            mastered_set = set(session.get("mastered", []))
            round2 = [wid for wid in word_ids if wid not in mastered_set]
            if round2:
                session["round"] = 2
                session["completed"] = []
            else:
                session["round"] = 0  # done
        else:
            session["round"] = 0  # all done

    await _set_config(db, session_key, json.dumps(session))
    await db.commit()

    # Count remaining
    remaining = [wid for wid in word_ids if wid not in completed]

    return {
        "category": new_cat,
        "review_count": review_count,
        "forget_count": forget_count,
        "next_review_date": str(next_review) if next_review else None,
        "round_complete": len(remaining) == 0,
        "next_round": session.get("round", 0),
        "remaining": len(remaining),
    }


@router.put("/settings")
async def update_settings(data: SettingsUpdate, db: AsyncSession = Depends(get_db)):
    await _set_config(db, "daily_new_words", str(data.daily_new_words))
    await db.commit()
    return {"daily_new_words": data.daily_new_words}


@router.post("/reset")
async def reset_session(db: AsyncSession = Depends(get_db)):
    """Reset today's review session (start over)."""
    today = date.today()
    session_key = f"session_{today.isoformat()}"
    await db.execute(text("DELETE FROM app_config WHERE key = :k"), {"k": session_key})
    await db.commit()
    return {"message": "Session reset"}
