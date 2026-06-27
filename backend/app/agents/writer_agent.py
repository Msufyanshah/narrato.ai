# backend/app/agents/writer_agent.py
import json
from openai import AsyncOpenAI
from app.config import settings
from app.constants.prompts import WRITER_AGENT_SYSTEM_PROMPT
from app.services.qdrant_client import retrieve_voice_memory

client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)

BANNED_PHRASES = [
    "comment YES", "drop a like", "share if you agree",
    "thoughts?", "agree or disagree?", "comment below",
    "double tap", "save this post", "repost this"
]

async def run_writer_agent(
    user_id: str,
    research: dict,
    persona: dict,
    voice_memory_samples: list[dict] = None,
    feedback: str = None
) -> dict:
    """
    Run the Writer Agent.
    Generates a LinkedIn post in the user's authentic voice.
    Matches Contract A2.
    """
    recommended_topic = research.get("recommended_topic")
    angle = research.get("angle")
    content_pillar = research.get("content_pillar", "general")

    # Fetch voice memory samples from Qdrant if not provided
    if voice_memory_samples is None:
        try:
            raw_samples = await retrieve_voice_memory(user_id, recommended_topic, top_k=5)
            # Format to match schema: content, pillar, performance_score
            voice_memory_samples = [
                {
                    "content": s["content"],
                    "pillar": s.get("type") or s.get("pillar") or "general",
                    "performance_score": int(s.get("relevance_score", 0) * 100)
                }
                for s in raw_samples
            ]
        except Exception:
            voice_memory_samples = []

    # Format voice memory samples for prompt
    if voice_memory_samples:
        samples_formatted = ""
        for idx, sample in enumerate(voice_memory_samples):
            samples_formatted += f"\nExample {idx + 1} (Pillar: {sample.get('pillar')}):\n{sample.get('content')}\n"
    else:
        samples_formatted = "No voice samples available. Write in a clean, professional, yet engaging style."

    # Local mock fallback for offline/local testing
    if not settings.OPENAI_API_KEY or settings.OPENAI_API_KEY.startswith("mock") or settings.OPENAI_API_KEY == "sk-...":
        hook_text = f"The rise of {recommended_topic}."
        if len(hook_text) > 49:
            hook_text = hook_text[:46] + "..."

        post_content = f"""Hook: {hook_text}

Many developers expect naive pipelines to just work. 
But prompt engineering is not real software engineering.

We spent the last 3 months deploying complex systems in production.
Here are the three hard truths we discovered:
1. NAIVE RAG IS DEAD: Semantic search alone is not enough for complex reasoning. You need structure.
2. AGENTS REQUIRE FEEDBACK LOOPS: You must compile, test, and iterate your agent prompts like code.
3. HYBRID ORCHESTRATION WINS: Fully autonomous loops are too unstable. Combine state machines with LLM planners.

What is the biggest challenge you have faced when deploying AI systems to production?"""

        return {
            "status": "success",
            "post_content": post_content,
            "hook": hook_text,
            "word_count": len(post_content.split()),
            "estimated_read_time_seconds": int(len(post_content.split()) / 3),
            "content_pillar": content_pillar
        }

    # Format the writer prompt
    banned_str = ", ".join(f"'{p}'" for p in BANNED_PHRASES)
    system_prompt = WRITER_AGENT_SYSTEM_PROMPT.format(
        voice_samples=samples_formatted.strip(),
        tone=persona.get("tone", "professional"),
        content_goal=persona.get("content_goal", "build_authority"),
        unique_differentiator=persona.get("unique_differentiator", "AI specialist"),
        banned_phrases=banned_str,
        topic=recommended_topic,
        angle=angle
    )

    user_content = f"Write the post now based on the topic: {recommended_topic}\nAngle: {angle}."
    if feedback:
        user_content += f"\n\nReviewer Feedback to fix: {feedback}\nEnsure you address this feedback completely in your rewrite."

    try:
        response = await client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content}
            ],
            response_format={"type": "json_object"}
        )

        output = json.loads(response.choices[0].message.content)
        # Verify schema
        if "post_content" in output:
            output["status"] = "success"
            # Ensure words and read time are computed
            words = len(output["post_content"].split())
            output["word_count"] = words
            output["estimated_read_time_seconds"] = int(words / 3)
            # Default content pillar if missing
            if "content_pillar" not in output:
                output["content_pillar"] = content_pillar
            # Extract hook if missing
            if "hook" not in output:
                output["hook"] = output["post_content"].split("\n")[0]
            return output
        else:
            return {
                "status": "failed",
                "reason": "Agent output missing post_content",
                "retry_suggested": True
            }

    except Exception as e:
        return {
            "status": "failed",
            "reason": f"Writer agent execution failed: {str(e)}",
            "retry_suggested": True
        }
