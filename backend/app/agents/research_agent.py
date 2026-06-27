# backend/app/agents/research_agent.py
import json
from openai import AsyncOpenAI
from app.config import settings
from app.constants.prompts import RESEARCH_AGENT_SYSTEM_PROMPT

client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)

# Tool definitions
RESEARCH_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "web_search",
            "description": "Search the web for trending topics and recent content",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search query"}
                },
                "required": ["query"]
            }
        }
    }
]

async def mock_web_search(query: str) -> str:
    """Placeholder — replace with real search API (Serper/Tavily) in production."""
    return f"Search results for '{query}': AI agents trending strongly in 2026, focus on production deployment, testing frameworks, and multi-agent coordination patterns."

async def run_research_agent(
    niche: str,
    content_pillars: list[str],
    target_audience: str,
    avoid_topics: list[str],
    recent_post_topics: list[str]
) -> dict:
    """Run Research Agent. Returns ResearchAgentOutput matching Contract A1."""

    # Local mock fallback for offline/local testing
    if not settings.OPENAI_API_KEY or settings.OPENAI_API_KEY.startswith("mock") or settings.OPENAI_API_KEY == "sk-...":
        return {
            "status": "success",
            "recommended_topic": f"The rise of {niche} and practical agents in 2026",
            "angle": "Why naive wrapper apps are dying and deep workflow agents are the future.",
            "reasoning": f"Found strong interest in {niche} on GitHub and tech Twitter today.",
            "trend_score": 8.5,
            "sources": ["GitHub trending", "Hacker News"],
            "content_pillar": content_pillars[0] if content_pillars else "general",
            "estimated_competition": "medium"
        }

    user_context = f"""
Niche: {niche}
Content pillars: {', '.join(content_pillars)}
Target audience: {target_audience}
Avoid these topics: {', '.join(avoid_topics) if avoid_topics else 'none'}
Recent posts (avoid repeating): {', '.join(recent_post_topics) if recent_post_topics else 'none in last 14 days'}
"""

    messages = [
        {"role": "system", "content": RESEARCH_AGENT_SYSTEM_PROMPT},
        {"role": "user", "content": f"Find the best topic for this creator:\n{user_context}"}
    ]

    # Tool calling loop (max 5 iterations)
    for _ in range(5):
        response = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
            tools=RESEARCH_TOOLS,
            tool_choice="auto"
        )

        message = response.choices[0].message

        if message.tool_calls:
            messages.append(message)
            for tool_call in message.tool_calls:
                if tool_call.function.name == "web_search":
                    args = json.loads(tool_call.function.arguments)
                    result = await mock_web_search(args["query"])
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": result
                    })
        else:
            # Final response
            try:
                output = json.loads(message.content)
                # Validate content_pillar is in user's pillars
                if output.get("content_pillar") not in content_pillars:
                    output["content_pillar"] = content_pillars[0] if content_pillars else "general"
                return output
            except json.JSONDecodeError:
                return {
                    "status": "failed",
                    "reason": "Agent returned invalid JSON",
                    "retry_suggested": True
                }

    return {"status": "failed", "reason": "Max tool call iterations reached", "retry_suggested": True}
