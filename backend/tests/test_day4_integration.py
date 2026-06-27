import sys
import os
import asyncio

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.agents.research_agent import run_research_agent
from app.agents.writer_agent import run_writer_agent
from app.services.qdrant_client import delete_user_documents

async def test_integration():
    TEST_USER = "integration-test-user-004"
    await delete_user_documents(TEST_USER)

    print("Step 1: Running Research Agent...")
    research_output = await run_research_agent(
        niche="Agentic AI",
        content_pillars=["Agentic AI", "RAG Systems"],
        target_audience="Developers",
        avoid_topics=["crypto"],
        recent_post_topics=[]
    )
    print("Research Output:", research_output)
    assert research_output["status"] == "success"

    print("\nStep 2: Feeding topic to Writer Agent...")
    persona = {
        "tone": "conversational",
        "content_goal": "build_authority",
        "unique_differentiator": "Deploying production agents since 2024"
    }

    writer_output = await run_writer_agent(
        user_id=TEST_USER,
        research=research_output,
        persona=persona
    )
    print("Writer Output:", writer_output)
    assert writer_output["status"] == "success"
    assert "post_content" in writer_output
    assert len(writer_output["hook"]) <= 49

    print("\nDay 4 Integration Checkpoint: PASS")

if __name__ == "__main__":
    asyncio.run(test_integration())
