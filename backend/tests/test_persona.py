import sys
import os
import asyncio
import httpx
from datetime import datetime

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.services.qdrant_client import retrieve_voice_memory
from app.agents.research_agent import run_research_agent

async def test_persona_flow():
    # 1. Create client and register user
    async with httpx.AsyncClient(base_url="http://localhost:8000") as client:
        import uuid
        uid = str(uuid.uuid4())[:8]
        email = f"persona_{uid}@autopost.ai"
        
        print("Registering user...")
        r = await client.post("/auth/register", json={"email": email, "password": "Check1234!", "name": "Creator"})
        assert r.status_code == 201
        token = r.json()["data"]["token"]
        headers = {"Authorization": f"Bearer {token}"}

        # 2. Verify GET /persona is 404
        print("Verifying GET /persona 404 (initially empty)...")
        r = await client.get("/persona", headers=headers)
        assert r.status_code == 404
        assert r.json()["error"]["code"] == "PERSONA_NOT_FOUND"

        # 3. Create persona
        print("Creating persona...")
        payload = {
            "name": "Creator Pro",
            "headline": "AI Engineering Consultant",
            "niche": "Agentic AI",
            "content_pillars": ["Agentic AI", "RAG Systems", "Tech Startups"],
            "tone": "bold",
            "target_audience": "Software Developers",
            "content_goal": "build_authority",
            "posting_frequency": "3x_week",
            "avoid_topics": ["politics", "gaming"],
            "unique_differentiator": "Building real agents in production since 2024"
        }
        r = await client.post("/persona", json=payload, headers=headers)
        print("POST /persona status:", r.status_code)
        assert r.status_code == 200
        res = r.json()
        assert res["success"] is True
        data = res["data"]
        assert data["niche"] == "Agentic AI"
        assert data["tone"] == "bold"
        user_uuid = data["user_id"]

        # 4. Verify GET /persona works now
        print("Verifying GET /persona...")
        r = await client.get("/persona", headers=headers)
        assert r.status_code == 200
        assert r.json()["data"]["name"] == "Creator Pro"

        # 5. Verify Qdrant auto-embedding of persona note (TASK-011)
        print("Verifying Qdrant auto-embedding of persona note...")
        results = await retrieve_voice_memory(
            user_id=user_uuid,
            topic="Agentic AI production differentiator",
            top_k=3
        )
        assert len(results) > 0, "No voice memory found!"
        has_persona_note = any(item["type"] == "persona_note" for item in results)
        assert has_persona_note is True, "Persona note was NOT auto-embedded!"
        print("Auto-embedded persona note found in Qdrant successfully!")

        # 6. Verify Research Agent output structure (TASK-013)
        print("Running Research Agent...")
        research_res = await run_research_agent(
            niche=data["niche"],
            content_pillars=data["content_pillars"],
            target_audience=data["target_audience"],
            avoid_topics=data["avoid_topics"],
            recent_post_topics=[]
        )
        print("Research Agent Output:", research_res)
        assert research_res["status"] == "success"
        assert "recommended_topic" in research_res
        assert "angle" in research_res
        assert "content_pillar" in research_res
        assert research_res["content_pillar"] in data["content_pillars"]
        print("Research Agent verified successfully!")

        print("\nALL DAY 3 TESTS PASSED!")

if __name__ == "__main__":
    asyncio.run(test_persona_flow())
