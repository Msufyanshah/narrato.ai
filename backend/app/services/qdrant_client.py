import uuid
from qdrant_client import QdrantClient
from qdrant_client.models import PointStruct, Filter, FieldCondition, MatchValue
from app.config import settings
from app.services.embeddings import embed_text, embed_batch

def get_client() -> QdrantClient:
    return QdrantClient(url=settings.QDRANT_URL, api_key=settings.QDRANT_API_KEY or None, timeout=30.0)

COLLECTION = "user_voice_memory"

async def upsert_document(
    user_id: str,
    content: str,
    doc_type: str,            # "past_post" | "persona_note"
    metadata: dict = None
) -> str:
    """Store a document in voice memory. Returns the document ID."""
    vector = await embed_text(content)
    doc_id = str(uuid.uuid4())

    client = get_client()
    client.upsert(
        collection_name=COLLECTION,
        points=[PointStruct(
            id=doc_id,
            vector=vector,
            payload={
                "user_id": user_id,
                "type": doc_type,
                "content": content,
                "metadata": metadata or {}
            }
        )]
    )
    return doc_id

async def upsert_batch(
    user_id: str,
    documents: list[dict]      # each: {content, type, metadata}
) -> list[str]:
    """Store multiple documents efficiently."""
    texts = [d["content"] for d in documents]
    vectors = await embed_batch(texts)

    points = []
    ids = []
    for doc, vector in zip(documents, vectors):
        doc_id = str(uuid.uuid4())
        ids.append(doc_id)
        points.append(PointStruct(
            id=doc_id,
            vector=vector,
            payload={
                "user_id": user_id,
                "type": doc.get("type", "past_post"),
                "content": doc["content"],
                "metadata": doc.get("metadata", {})
            }
        ))

    client = get_client()
    client.upsert(collection_name=COLLECTION, points=points)
    return ids

async def retrieve_voice_memory(
    user_id: str,
    topic: str,
    top_k: int = 5
) -> list[dict]:
    """Semantic search for voice memory samples relevant to a topic."""
    query_vector = await embed_text(topic)
    client = get_client()

    results = client.search(
        collection_name=COLLECTION,
        query_vector=query_vector,
        query_filter=Filter(
            must=[FieldCondition(key="user_id", match=MatchValue(value=user_id))]
        ),
        limit=top_k,
        with_payload=True
    )

    return [
        {
            "content": r.payload["content"],
            "type": r.payload["type"],
            "metadata": r.payload.get("metadata", {}),
            "relevance_score": r.score
        }
        for r in results
    ]

async def count_user_documents(user_id: str) -> int:
    """Count how many memory documents a user has."""
    client = get_client()
    result = client.count(
        collection_name=COLLECTION,
        count_filter=Filter(
            must=[FieldCondition(key="user_id", match=MatchValue(value=user_id))]
        )
    )
    return result.count

async def delete_user_documents(user_id: str) -> int:
    """Delete all voice memory for a user. Returns count deleted."""
    count = await count_user_documents(user_id)
    if count == 0:
        return 0
    client = get_client()
    client.delete(
        collection_name=COLLECTION,
        points_selector=Filter(
            must=[FieldCondition(key="user_id", match=MatchValue(value=user_id))]
        )
    )
    return count

async def delete_user_persona_notes(user_id: str) -> None:
    """Delete only the persona note documents for a user to avoid duplicates."""
    client = get_client()
    client.delete(
        collection_name=COLLECTION,
        points_selector=Filter(
            must=[
                FieldCondition(key="user_id", match=MatchValue(value=user_id)),
                FieldCondition(key="type", match=MatchValue(value="persona_note"))
            ]
        )
    )

