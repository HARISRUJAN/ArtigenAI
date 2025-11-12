from typing import List, Optional
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct
from app.core.config import settings

class VectorService:
    def __init__(self):
        self.client = None
        self.collection_name = settings.qdrant_collection_name
        self._initialized = False
    
    def _init_client(self):
        """Lazy initialization of Qdrant client"""
        if not self._initialized:
            # Support both local and cloud Qdrant
            if settings.qdrant_api_key:
                # Qdrant Cloud with API key
                self.client = QdrantClient(
                    url=settings.qdrant_url,
                    api_key=settings.qdrant_api_key
                )
            else:
                # Local Qdrant or cloud without API key
                self.client = QdrantClient(url=settings.qdrant_url)
            self._ensure_collection()
            self._initialized = True
    
    def _ensure_collection(self):
        """Create collection if it doesn't exist"""
        if not self.client:
            self._init_client()
        collections = self.client.get_collections().collections
        collection_names = [col.name for col in collections]
        
        if self.collection_name not in collection_names:
            self.client.create_collection(
                collection_name=self.collection_name,
                vectors_config=VectorParams(
                    size=768,  # Nomic embed-text-v1 embedding size (768 dimensions)
                    distance=Distance.COSINE
                )
            )
    
    def add_embeddings(
        self,
        embeddings: List[List[float]],
        ids: List[str],
        payloads: List[dict]
    ):
        """Add embeddings to Qdrant"""
        if not self._initialized:
            self._init_client()
        points = [
            PointStruct(
                id=point_id,
                vector=embedding,
                payload=payload
            )
            for point_id, embedding, payload in zip(ids, embeddings, payloads)
        ]
        
        self.client.upsert(
            collection_name=self.collection_name,
            points=points
        )
    
    def search(
        self,
        query_embedding: List[float],
        top_k: int = 5,
        filter_conditions: Optional[dict] = None
    ) -> List[dict]:
        """Search for similar embeddings"""
        if not self._initialized:
            self._init_client()
        search_result = self.client.search(
            collection_name=self.collection_name,
            query_vector=query_embedding,
            limit=top_k,
            query_filter=filter_conditions
        )
        
        results = []
        for result in search_result:
            results.append({
                "id": result.id,
                "score": result.score,
                "payload": result.payload
            })
        
        return results
    
    def delete_points(self, point_ids: List[str]):
        """Delete points by IDs"""
        if not self._initialized:
            self._init_client()
        self.client.delete(
            collection_name=self.collection_name,
            points_selector=point_ids
        )


# Lazy initialization - will connect when first used
vector_service = VectorService()

