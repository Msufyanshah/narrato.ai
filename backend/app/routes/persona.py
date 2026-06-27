from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.models.user import User
from app.routes.auth import require_auth
from sqlalchemy import select
from app.models.persona import Persona
from app.schemas.persona import SeedPostsRequest, SeedPostsResponse, PersonaCreateRequest, PersonaResponse
from app.services.qdrant_client import (
    upsert_batch, count_user_documents,
    upsert_document, delete_user_persona_notes
)
from app.utils.envelope import EnvelopedRoute

router = APIRouter(prefix="/persona", tags=["persona"], route_class=EnvelopedRoute)

MIN_POSTS_REQUIRED = 3

@router.post("/seed-posts", response_model=SeedPostsResponse)
async def seed_posts(
    body: SeedPostsRequest,
    current_user: User = Depends(require_auth),
    db: AsyncSession = Depends(get_db)
):
    if len(body.posts) < MIN_POSTS_REQUIRED:
        raise HTTPException(
            status_code=400,
            detail={
                "code": "MIN_POSTS_NOT_MET",
                "message": f"Please provide at least {MIN_POSTS_REQUIRED} past posts to seed your voice memory."
            }
        )

    documents = [
        {
            "content": post.content,
            "type": "past_post",
            "metadata": {
                "approximate_date": post.approximate_date,
                "pillar": "general"
            }
        }
        for post in body.posts
    ]

    indexed = 0
    failed = 0
    try:
        await upsert_batch(str(current_user.id), documents)
        indexed = len(documents)
    except Exception as e:
        failed = len(documents)

    total = await count_user_documents(str(current_user.id))
    return SeedPostsResponse(indexed=indexed, failed=failed, total_in_memory=total)

@router.post("", response_model=PersonaResponse)
async def create_or_update_persona(
    body: PersonaCreateRequest,
    current_user: User = Depends(require_auth),
    db: AsyncSession = Depends(get_db)
):
    # Check content pillars limit (max 3)
    if len(body.content_pillars) > 3:
        raise HTTPException(
            status_code=400,
            detail={
                "code": "TOO_MANY_PILLARS",
                "message": "You can define a maximum of 3 content pillars."
            }
        )

    stmt = select(Persona).where(Persona.user_id == current_user.id)
    res = await db.execute(stmt)
    persona = res.scalar_one_or_none()

    if not persona:
        persona = Persona(user_id=current_user.id)
        db.add(persona)

    # Update fields
    persona.name = body.name
    persona.headline = body.headline
    persona.niche = body.niche
    persona.content_pillars = body.content_pillars
    persona.tone = body.tone
    persona.target_audience = body.target_audience
    persona.content_goal = body.content_goal
    persona.posting_frequency = body.posting_frequency
    persona.avoid_topics = body.avoid_topics
    persona.unique_differentiator = body.unique_differentiator

    await db.commit()
    await db.refresh(persona)

    # First delete old persona notes to avoid duplicates
    await delete_user_persona_notes(str(current_user.id))

    persona_note_text = f"""
Name: {persona.name}
Headline: {persona.headline}
Niche: {persona.niche}
Content pillars: {', '.join(persona.content_pillars)}
Target audience: {persona.target_audience}
Unique differentiator: {persona.unique_differentiator}
Content goal: {persona.content_goal}
Tone: {persona.tone}
"""

    await upsert_document(
        user_id=str(current_user.id),
        content=persona_note_text.strip(),
        doc_type="persona_note",
        metadata={
            "niche": persona.niche,
            "pillars": persona.content_pillars,
            "tone": persona.tone
        }
    )

    return PersonaResponse(
        id=str(persona.id),
        user_id=str(persona.user_id),
        name=persona.name,
        headline=persona.headline,
        niche=persona.niche,
        content_pillars=persona.content_pillars,
        tone=persona.tone,
        target_audience=persona.target_audience,
        content_goal=persona.content_goal,
        posting_frequency=persona.posting_frequency,
        avoid_topics=persona.avoid_topics or [],
        unique_differentiator=persona.unique_differentiator,
        updated_at=persona.updated_at.isoformat()
    )

@router.get("", response_model=PersonaResponse)
async def get_persona(
    current_user: User = Depends(require_auth),
    db: AsyncSession = Depends(get_db)
):
    stmt = select(Persona).where(Persona.user_id == current_user.id)
    res = await db.execute(stmt)
    persona = res.scalar_one_or_none()

    if not persona:
        raise HTTPException(
            status_code=404,
            detail={
                "code": "PERSONA_NOT_FOUND",
                "message": "No creator persona found for this account. Please create one."
            }
        )

    return PersonaResponse(
        id=str(persona.id),
        user_id=str(persona.user_id),
        name=persona.name,
        headline=persona.headline,
        niche=persona.niche,
        content_pillars=persona.content_pillars,
        tone=persona.tone,
        target_audience=persona.target_audience,
        content_goal=persona.content_goal,
        posting_frequency=persona.posting_frequency,
        avoid_topics=persona.avoid_topics or [],
        unique_differentiator=persona.unique_differentiator,
        updated_at=persona.updated_at.isoformat()
    )
