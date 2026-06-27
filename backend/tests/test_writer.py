import sys
import os
import asyncio

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.services.qdrant_client import upsert_batch, delete_user_documents
from app.agents.writer_agent import run_writer_agent

async def test_writer_agent():
    TEST_USER = 'test-writer-user-001'

    # Clean up and seed 3 past posts for voice memory influence
    print("Seeding voice memory...")
    await delete_user_documents(TEST_USER)
    
    samples = [
        {"content": "Building autonomous AI agents requires a solid planning and tooling structure. Naive RAG is dead.", "type": "past_post"},
        {"content": "When designing agent prompt compilers, keep prompts static and pass dynamic contexts. This is a must.", "type": "past_post"},
        {"content": "Alembic migrations are the backbone of database schema versioning in SQL-based Python setups.", "type": "past_post"}
    ]
    await upsert_batch(TEST_USER, samples)

    # 2. Setup mock inputs matching schemas
    research = {
        "recommended_topic": "Agent planning loops",
        "angle": "Why hierarchical agents outperform single flat loops in production",
        "reasoning": "Observed high failure rates in flat loops during testing",
        "sources": ["Local experiments"],
        "content_pillar": "Agentic AI"
    }

    persona = {
        "tone": "bold",
        "content_goal": "build_authority",
        "unique_differentiator": "Deploys custom agents in production since 2024"
    }

    print("Running Writer Agent...")
    writer_res = await run_writer_agent(
        user_id=TEST_USER,
        research=research,
        persona=persona
    )

    print("Writer Agent Output:", writer_res)
    assert writer_res["status"] == "success"
    assert "post_content" in writer_res
    assert "hook" in writer_res
    assert len(writer_res["hook"]) <= 49, f"Hook length is {len(writer_res['hook'])}, expected <= 49"
    assert writer_res["word_count"] > 0
    assert writer_res["content_pillar"] == "Agentic AI"

    # Cleanup
    await delete_user_documents(TEST_USER)
    print("\nALL WRITER AGENT TESTS PASSED!")

if __name__ == "__main__":
    asyncio.run(test_writer_agent())
