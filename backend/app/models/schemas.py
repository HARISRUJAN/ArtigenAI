from pydantic import BaseModel, EmailStr
from typing import Optional, List, Dict
from datetime import datetime
from app.models.database import UserRole


# Auth schemas
class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    username: Optional[str] = None


class UserLogin(BaseModel):
    username: str
    password: str


class UserResponse(BaseModel):
    id: int
    username: str
    email: str
    role: UserRole
    is_active: bool
    
    class Config:
        from_attributes = True


# Scraping Origin schemas
class ScrapingOriginBase(BaseModel):
    name: str
    url: str
    frequency_hours: int = 24
    enabled: bool = True
    # Enhanced metadata fields (all optional for backward compatibility)
    country_code: Optional[str] = None
    topic_tags: Optional[List[str]] = None  # List of topic tags
    crawl_priority: Optional[int] = None  # 1-10 scale
    allowed_path_patterns: Optional[List[str]] = None  # List of regex patterns
    excluded_path_patterns: Optional[List[str]] = None  # List of regex patterns
    sitemap_url: Optional[str] = None


class ScrapingOriginCreate(ScrapingOriginBase):
    pass


class ScrapingOriginUpdate(BaseModel):
    name: Optional[str] = None
    url: Optional[str] = None
    frequency_hours: Optional[int] = None
    enabled: Optional[bool] = None
    country_code: Optional[str] = None
    topic_tags: Optional[List[str]] = None
    crawl_priority: Optional[int] = None
    allowed_path_patterns: Optional[List[str]] = None
    excluded_path_patterns: Optional[List[str]] = None
    sitemap_url: Optional[str] = None


class ScrapingOriginResponse(ScrapingOriginBase):
    id: int
    last_run: Optional[datetime] = None
    last_status: Optional[str] = None
    qdrant_status: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


# Document schemas
class DocumentBase(BaseModel):
    title: str
    source: str
    url: Optional[str] = None
    content: str
    metadata: Optional[str] = None


class DocumentCreate(DocumentBase):
    origin_id: Optional[int] = None


class DocumentResponse(DocumentBase):
    id: int
    ingestion_date: datetime
    origin_id: Optional[int] = None
    
    class Config:
        from_attributes = True


# Chunk schemas
class ChunkResponse(BaseModel):
    id: int
    document_id: int
    content: str
    chunk_index: int
    metadata: Optional[str] = None
    
    class Config:
        from_attributes = True


# RAG schemas
class DocumentChunk(BaseModel):
    content: str
    document_title: str
    document_source: str
    document_url: Optional[str] = None
    chunk_index: int
    entities: Optional[List[Dict]] = None  # Extracted entities from spaCy NER
    metadata: Optional[dict] = None


class RAGQuery(BaseModel):
    question: str
    top_k: int = 5
    use_web_fallback: bool = False  # Default False to preserve existing behavior


class RAGResponse(BaseModel):
    answer: str
    citations: List[DocumentChunk]


# Ingestion schemas
class DocumentIngest(BaseModel):
    title: str
    source: str
    url: Optional[str] = None
    content: str
    metadata: Optional[dict] = None


# Health schemas
class OriginStatus(BaseModel):
    origin_id: int
    origin_name: str
    last_run: Optional[datetime] = None
    last_status: Optional[str] = None
    qdrant_status: Optional[str] = None
    enabled: bool


class QdrantHealth(BaseModel):
    connected: bool
    url: str
    collection_name: str
    collection_exists: bool
    points_count: Optional[int] = None
    vector_size: Optional[int] = None
    error: Optional[str] = None


class QdrantCollectionsHealth(BaseModel):
    """Health status for both Qdrant collections"""
    connected: bool
    url: str
    legacy_collection: Optional[QdrantHealth] = None  # Old collection (aigov_documents)
    semantic_collection: Optional[QdrantHealth] = None  # New semantic collection
    error: Optional[str] = None


class SystemHealth(BaseModel):
    status: str
    origins: List[OriginStatus]
    qdrant: Optional[QdrantHealth] = None  # Legacy: single collection
    qdrant_collections: Optional[QdrantCollectionsHealth] = None  # New: both collections


# Dashboard schemas
class DashboardOverview(BaseModel):
    total_origins: int
    active_origins: int
    crawls_last_24h: int
    docs_ingested_last_24h: int
    policy_relevance_ratio_last_24h: float
    crawl_error_rate_last_24h: float


class OriginDashboardSummary(BaseModel):
    id: int
    name: str
    url: str
    country_code: Optional[str] = None
    topic_tags: Optional[List[str]] = None
    enabled: bool
    crawl_priority: Optional[int] = None
    frequency_hours: int
    last_run: Optional[datetime] = None
    last_status: Optional[str] = None
    qdrant_status: Optional[str] = None
    next_run: Optional[datetime] = None
    avg_change_rate: Optional[float] = None
    policy_relevant_ratio: Optional[float] = None


class OriginDetailResponse(BaseModel):
    id: int
    name: str
    url: str
    country_code: Optional[str] = None
    topic_tags: Optional[List[str]] = None
    enabled: bool
    crawl_priority: Optional[int] = None
    frequency_hours: int
    allowed_path_patterns: Optional[List[str]] = None
    excluded_path_patterns: Optional[List[str]] = None
    sitemap_url: Optional[str] = None
    last_run: Optional[datetime] = None
    last_status: Optional[str] = None
    qdrant_status: Optional[str] = None
    next_run: Optional[datetime] = None
    documents_count: int
    chunks_count: int
    recent_jobs: List[Dict] = []
    latest_error: Optional[str] = None


class OriginConfigUpdate(BaseModel):
    enabled: Optional[bool] = None
    frequency_hours: Optional[int] = None
    max_pages_per_run: Optional[int] = None
    max_depth: Optional[int] = None
    priority_score_threshold: Optional[float] = None


class JobSummary(BaseModel):
    job_id: str
    origin_id: Optional[int] = None
    origin_name: Optional[str] = None
    mode: str
    trigger_type: str
    start_time: datetime
    end_time: Optional[datetime] = None
    duration_seconds: Optional[float] = None
    status: str
    pages_attempted: int
    pages_succeeded: int
    policy_relevant_pages: int
    new_docs_ingested: int
    error_summary: Optional[str] = None


class JobDetailResponse(BaseModel):
    job_id: str
    origin_id: Optional[int] = None
    origin_name: Optional[str] = None
    mode: str
    trigger_type: str
    start_time: datetime
    end_time: Optional[datetime] = None
    duration_seconds: Optional[float] = None
    status: str
    pages_attempted: int
    pages_succeeded: int
    policy_relevant_pages: int
    new_docs_ingested: int
    error_summary: Optional[str] = None
    error_breakdown: Dict[str, int] = {}
    top_errors: List[str] = []
    related_documents: List[int] = []


class PaginatedResponse(BaseModel):
    items: List[Dict]
    total: int
    page: int
    limit: int
    pages: int


class DocumentSummary(BaseModel):
    id: int
    title: str
    origin_id: Optional[int] = None
    origin_name: Optional[str] = None
    url: Optional[str] = None
    source_type: str
    version: Optional[int] = None
    last_modified: Optional[datetime] = None
    ingestion_date: datetime
    chunks_count: int
    relevance_flag: Optional[str] = None
    dedup_status: Optional[str] = None


class DocumentDetailResponse(BaseModel):
    id: int
    title: str
    source: str
    url: Optional[str] = None
    origin_id: Optional[int] = None
    origin_name: Optional[str] = None
    ingestion_date: datetime
    chunks_count: int
    metadata: Optional[Dict] = None
    chunks_summary: List[Dict] = []
    version_history: List[Dict] = []


class SettingsResponse(BaseModel):
    crawling: Dict
    realtime_web: Dict
    rag: Dict
    data_retention: Dict


class SettingsUpdate(BaseModel):
    crawling: Optional[Dict] = None
    realtime_web: Optional[Dict] = None
    rag: Optional[Dict] = None
    data_retention: Optional[Dict] = None

