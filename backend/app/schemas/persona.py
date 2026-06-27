from pydantic import BaseModel
from typing import Optional

class SeedPost(BaseModel):
    content: str
    approximate_date: Optional[str] = None

class SeedPostsRequest(BaseModel):
    posts: list[SeedPost]

class SeedPostsResponse(BaseModel):
    indexed: int
    failed: int
    total_in_memory: int

class PersonaCreateRequest(BaseModel):
    name: str
    headline: str
    niche: str
    content_pillars: list[str]
    tone: str
    target_audience: str
    content_goal: str
    posting_frequency: str
    avoid_topics: Optional[list[str]] = []
    unique_differentiator: str

class PersonaResponse(BaseModel):
    id: str
    user_id: str
    name: str
    headline: str
    niche: str
    content_pillars: list[str]
    tone: str
    target_audience: str
    content_goal: str
    posting_frequency: str
    avoid_topics: list[str]
    unique_differentiator: str
    updated_at: str

