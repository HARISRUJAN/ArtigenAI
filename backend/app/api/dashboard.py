"""
Admin Dashboard API endpoints for monitoring crawling and ingestion.
All endpoints are read-only monitoring or safe configuration updates.
"""
import logging
import json
from typing import List, Optional, Dict
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_
from app.models.database import get_db, ScrapingOrigin, Document, Chunk
from app.core.security import get_current_active_admin
from app.models.schemas import (
    DashboardOverview,
    OriginDashboardSummary,
    OriginDetailResponse,
    OriginConfigUpdate,
    JobSummary,
    JobDetailResponse,
    PaginatedResponse,
    DocumentSummary,
    DocumentDetailResponse,
    SettingsResponse,
    SettingsUpdate
)
from app.core.config import settings
from app.core.scheduler import schedule_origin

logger = logging.getLogger(__name__)

router = APIRouter()

# Import job status from crawl module
try:
    from app.api.crawl import _job_status
except ImportError:
    _job_status = {}


@router.get("/overview", response_model=DashboardOverview)
async def get_dashboard_overview(
    db: Session = Depends(get_db),
    current_user = Depends(get_current_active_admin)
):
    """
    Get high-level KPIs for dashboard overview.
    
    Returns:
        DashboardOverview with key metrics for last 24 hours
    """
    now = datetime.utcnow()
    last_24h = now - timedelta(hours=24)
    
    # Total origins
    total_origins = db.query(ScrapingOrigin).count()
    
    # Active origins (enabled)
    active_origins = db.query(ScrapingOrigin).filter(ScrapingOrigin.enabled == True).count()
    
    # Documents ingested in last 24h
    docs_last_24h = db.query(Document).filter(
        Document.ingestion_date >= last_24h
    ).count()
    
    # Crawl jobs in last 24h (from in-memory job tracking)
    crawls_last_24h = 0
    crawl_errors = 0
    total_pages_crawled = 0
    policy_relevant_pages = 0
    
    for job_id, job_data in _job_status.items():
        start_time_str = job_data.get("started_at") or job_data.get("queued_at")
        if start_time_str:
            try:
                start_time = datetime.fromisoformat(start_time_str.replace('Z', '+00:00'))
                if start_time >= last_24h:
                    crawls_last_24h += 1
                    if job_data.get("status") == "failed":
                        crawl_errors += 1
                    pages_crawled = job_data.get("pages_crawled", 0)
                    total_pages_crawled += pages_crawled
                    # Estimate policy relevant from metadata if available
                    if job_data.get("metadata", {}).get("relevance_score"):
                        policy_relevant_pages += pages_crawled
            except (ValueError, TypeError):
                pass
    
    # Calculate error rate
    crawl_error_rate = (crawl_errors / crawls_last_24h * 100) if crawls_last_24h > 0 else 0.0
    
    # Calculate policy relevance ratio
    policy_relevance_ratio = (policy_relevant_pages / total_pages_crawled * 100) if total_pages_crawled > 0 else 0.0
    
    return DashboardOverview(
        total_origins=total_origins,
        active_origins=active_origins,
        crawls_last_24h=crawls_last_24h,
        docs_ingested_last_24h=docs_last_24h,
        policy_relevance_ratio_last_24h=round(policy_relevance_ratio, 2),
        crawl_error_rate_last_24h=round(crawl_error_rate, 2)
    )


@router.get("/overview/timeseries")
async def get_dashboard_timeseries(
    days: int = Query(7, ge=1, le=30, description="Number of days to include"),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_active_admin)
):
    """
    Get time-series data for charts (crawls and documents over time).
    
    Returns:
        Dict with 'crawls' and 'documents' arrays, each containing daily counts
    """
    now = datetime.utcnow()
    start_date = now - timedelta(days=days)
    
    # Initialize date buckets
    date_buckets = {}
    for i in range(days):
        date = (start_date + timedelta(days=i)).date()
        date_buckets[date] = {"crawls": 0, "documents": 0}
    
    # Aggregate documents by date
    documents = db.query(Document).filter(
        Document.ingestion_date >= start_date
    ).all()
    
    for doc in documents:
        if doc.ingestion_date:
            doc_date = doc.ingestion_date.date()
            if doc_date in date_buckets:
                date_buckets[doc_date]["documents"] += 1
    
    # Aggregate crawls by date (from job tracking)
    for job_id, job_data in _job_status.items():
        start_time_str = job_data.get("started_at") or job_data.get("queued_at")
        if start_time_str:
            try:
                start_time = datetime.fromisoformat(start_time_str.replace('Z', '+00:00'))
                if start_time >= start_date:
                    crawl_date = start_time.date()
                    if crawl_date in date_buckets:
                        date_buckets[crawl_date]["crawls"] += 1
            except (ValueError, TypeError):
                pass
    
    # Convert to arrays for charting
    crawls_data = [
        {"date": str(date), "count": data["crawls"]}
        for date, data in sorted(date_buckets.items())
    ]
    
    documents_data = [
        {"date": str(date), "count": data["documents"]}
        for date, data in sorted(date_buckets.items())
    ]
    
    return {
        "crawls": crawls_data,
        "documents": documents_data
    }


@router.get("/origins", response_model=List[OriginDashboardSummary])
async def get_dashboard_origins(
    db: Session = Depends(get_db),
    current_user = Depends(get_current_active_admin)
):
    """
    List all origins with extended metadata for dashboard.
    
    Returns:
        List of OriginDashboardSummary with schedule and performance metrics
    """
    origins = db.query(ScrapingOrigin).all()
    results = []
    
    for origin in origins:
        # Parse JSON fields
        topic_tags = None
        if origin.topic_tags:
            try:
                topic_tags = json.loads(origin.topic_tags)
            except:
                pass
        
        # Calculate next_run
        next_run = None
        if origin.last_run and origin.frequency_hours:
            next_run = origin.last_run + timedelta(hours=origin.frequency_hours)
        
        # Calculate policy relevant ratio from documents
        policy_relevant_ratio = None
        docs = db.query(Document).filter(Document.origin_id == origin.id).all()
        if docs:
            relevant_count = 0
            for doc in docs:
                if doc.document_metadata:
                    try:
                        meta = json.loads(doc.document_metadata)
                        if meta.get("relevance_score", 0) >= 3:  # Threshold
                            relevant_count += 1
                    except:
                        pass
            policy_relevant_ratio = (relevant_count / len(docs) * 100) if docs else 0.0
        
        results.append(OriginDashboardSummary(
            id=origin.id,
            name=origin.name,
            url=origin.url,
            country_code=origin.country_code,
            topic_tags=topic_tags,
            enabled=origin.enabled,
            crawl_priority=origin.crawl_priority,
            frequency_hours=origin.frequency_hours,
            last_run=origin.last_run,
            last_status=origin.last_status,
            qdrant_status=origin.qdrant_status,
            next_run=next_run,
            avg_change_rate=None,  # Future: calculate from change detection
            policy_relevant_ratio=round(policy_relevant_ratio, 2) if policy_relevant_ratio is not None else None
        ))
    
    return results


@router.get("/origins/{origin_id}", response_model=OriginDetailResponse)
async def get_dashboard_origin_detail(
    origin_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_active_admin)
):
    """
    Get detailed information about a specific origin.
    
    Returns:
        OriginDetailResponse with metadata, recent jobs, and document counts
    """
    origin = db.query(ScrapingOrigin).filter(ScrapingOrigin.id == origin_id).first()
    if not origin:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Origin not found"
        )
    
    # Parse JSON fields
    topic_tags = None
    allowed_paths = None
    excluded_paths = None
    if origin.topic_tags:
        try:
            topic_tags = json.loads(origin.topic_tags)
        except:
            pass
    if origin.allowed_path_patterns:
        try:
            allowed_paths = json.loads(origin.allowed_path_patterns)
        except:
            pass
    if origin.excluded_path_patterns:
        try:
            excluded_paths = json.loads(origin.excluded_path_patterns)
        except:
            pass
    
    # Calculate next_run
    next_run = None
    if origin.last_run and origin.frequency_hours:
        next_run = origin.last_run + timedelta(hours=origin.frequency_hours)
    
    # Get document and chunk counts
    docs_count = db.query(Document).filter(Document.origin_id == origin_id).count()
    chunks_count = db.query(Chunk).join(Document).filter(Document.origin_id == origin_id).count()
    
    # Get recent jobs (from in-memory tracking, filter by origin)
    recent_jobs = []
    for job_id, job_data in _job_status.items():
        if job_data.get("origin_id") == origin_id or job_data.get("triggered_by"):
            # Try to extract origin info from job
            job_summary = {
                "job_id": job_id,
                "status": job_data.get("status", "unknown"),
                "started_at": job_data.get("started_at") or job_data.get("queued_at"),
                "completed_at": job_data.get("completed_at"),
                "pages_crawled": job_data.get("pages_crawled", 0),
                "mode": job_data.get("mode", "unknown")
            }
            recent_jobs.append(job_summary)
    
    # Sort by start time, get last 5
    recent_jobs.sort(key=lambda x: x.get("started_at", ""), reverse=True)
    recent_jobs = recent_jobs[:5]
    
    # Extract latest error
    latest_error = None
    if origin.last_status and "failed" in origin.last_status.lower():
        latest_error = origin.last_status
    elif origin.qdrant_status and "failed" in origin.qdrant_status.lower():
        latest_error = origin.qdrant_status
    
    return OriginDetailResponse(
        id=origin.id,
        name=origin.name,
        url=origin.url,
        country_code=origin.country_code,
        topic_tags=topic_tags,
        enabled=origin.enabled,
        crawl_priority=origin.crawl_priority,
        frequency_hours=origin.frequency_hours,
        allowed_path_patterns=allowed_paths,
        excluded_path_patterns=excluded_paths,
        sitemap_url=origin.sitemap_url,
        last_run=origin.last_run,
        last_status=origin.last_status,
        qdrant_status=origin.qdrant_status,
        next_run=next_run,
        documents_count=docs_count,
        chunks_count=chunks_count,
        recent_jobs=recent_jobs,
        latest_error=latest_error
    )


@router.patch("/origins/{origin_id}/config", response_model=OriginDetailResponse)
async def update_origin_config(
    origin_id: int,
    config: OriginConfigUpdate,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_active_admin)
):
    """
    Update safe configuration for an origin.
    
    Only updates fields that don't affect running crawls:
    - enabled: Toggle origin on/off
    - frequency_hours: Update crawl frequency
    - max_pages_per_run: Store in metadata (future)
    - max_depth: Store in metadata (future)
    - priority_score_threshold: Store in metadata (future)
    """
    origin = db.query(ScrapingOrigin).filter(ScrapingOrigin.id == origin_id).first()
    if not origin:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Origin not found"
        )
    
    # Update enabled flag
    if config.enabled is not None:
        origin.enabled = config.enabled
    
    # Update frequency_hours (will reschedule)
    if config.frequency_hours is not None:
        if config.frequency_hours < 1:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="frequency_hours must be at least 1"
            )
        origin.frequency_hours = config.frequency_hours
    
    # Store other config in metadata (future: add dedicated fields)
    # For now, we'll skip max_pages_per_run, max_depth, priority_score_threshold
    # as they're not yet stored per-origin in the database
    
    db.commit()
    db.refresh(origin)
    
    # Reschedule origin if frequency changed or enabled status changed
    schedule_origin(origin)
    
    # Return updated origin detail
    return await get_dashboard_origin_detail(origin_id, db, current_user)


@router.get("/jobs", response_model=PaginatedResponse)
async def get_dashboard_jobs(
    origin_id: Optional[int] = Query(None, description="Filter by origin ID"),
    status: Optional[str] = Query(None, description="Filter by status (queued/running/completed/failed)"),
    date_from: Optional[str] = Query(None, description="Filter from date (ISO format)"),
    date_to: Optional[str] = Query(None, description="Filter to date (ISO format)"),
    mode: Optional[str] = Query(None, description="Filter by mode (query/domain/scheduled/realtime_web)"),
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(20, ge=1, le=100, description="Items per page"),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_active_admin)
):
    """
    Get paginated list of crawl jobs with filters.
    
    Returns:
        PaginatedResponse with job summaries
    """
    # Parse date filters
    date_from_dt = None
    date_to_dt = None
    if date_from:
        try:
            date_from_dt = datetime.fromisoformat(date_from.replace('Z', '+00:00'))
        except:
            pass
    if date_to:
        try:
            date_to_dt = datetime.fromisoformat(date_to.replace('Z', '+00:00'))
        except:
            pass
    
    # Filter jobs from in-memory tracking
    filtered_jobs = []
    for job_id, job_data in _job_status.items():
        # Apply filters
        if origin_id is not None:
            job_origin_id = job_data.get("origin_id")
            if job_origin_id != origin_id:
                continue
        
        if status:
            job_status = job_data.get("status", "").lower()
            if job_status != status.lower():
                continue
        
        if mode:
            job_mode = job_data.get("mode", "").lower()
            if job_mode != mode.lower():
                continue
        
        # Date filter
        start_time_str = job_data.get("started_at") or job_data.get("queued_at")
        if start_time_str:
            try:
                start_time = datetime.fromisoformat(start_time_str.replace('Z', '+00:00'))
                if date_from_dt and start_time < date_from_dt:
                    continue
                if date_to_dt and start_time > date_to_dt:
                    continue
            except:
                pass
        
        # Get origin name
        origin_name = None
        if job_data.get("origin_id"):
            origin = db.query(ScrapingOrigin).filter(ScrapingOrigin.id == job_data["origin_id"]).first()
            if origin:
                origin_name = origin.name
        
        # Calculate duration
        duration_seconds = None
        start_time_str = job_data.get("started_at") or job_data.get("queued_at")
        end_time_str = job_data.get("completed_at") or job_data.get("failed_at")
        if start_time_str and end_time_str:
            try:
                start = datetime.fromisoformat(start_time_str.replace('Z', '+00:00'))
                end = datetime.fromisoformat(end_time_str.replace('Z', '+00:00'))
                duration_seconds = (end - start).total_seconds()
            except:
                pass
        
        # Determine trigger type
        trigger_type = "scheduler"
        if job_data.get("triggered_by"):
            if "realtime" in job_data.get("mode", "").lower():
                trigger_type = "realtime_fallback"
            else:
                trigger_type = "API"
        
        job_summary = {
            "job_id": job_id,
            "origin_id": job_data.get("origin_id"),
            "origin_name": origin_name,
            "mode": job_data.get("mode", "unknown"),
            "trigger_type": trigger_type,
            "start_time": start_time_str,
            "end_time": end_time_str,
            "duration_seconds": duration_seconds,
            "status": job_data.get("status", "unknown"),
            "pages_attempted": job_data.get("pages_attempted", job_data.get("pages_crawled", 0)),
            "pages_succeeded": job_data.get("pages_succeeded", job_data.get("pages_crawled", 0)),
            "policy_relevant_pages": job_data.get("policy_relevant_pages", 0),
            "new_docs_ingested": 1 if job_data.get("document_id") else 0,
            "error_summary": job_data.get("error")
        }
        filtered_jobs.append(job_summary)
    
    # Sort by start time (newest first)
    filtered_jobs.sort(key=lambda x: x.get("start_time", ""), reverse=True)
    
    # Paginate
    total = len(filtered_jobs)
    start_idx = (page - 1) * limit
    end_idx = start_idx + limit
    paginated_jobs = filtered_jobs[start_idx:end_idx]
    
    return PaginatedResponse(
        items=paginated_jobs,
        total=total,
        page=page,
        limit=limit,
        pages=(total + limit - 1) // limit
    )


@router.get("/jobs/{job_id}", response_model=JobDetailResponse)
async def get_dashboard_job_detail(
    job_id: str,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_active_admin)
):
    """
    Get detailed information about a specific crawl job.
    
    Returns:
        JobDetailResponse with error breakdown and related documents
    """
    job_data = _job_status.get(job_id)
    if not job_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found"
        )
    
    # Get origin name
    origin_name = None
    origin_id = job_data.get("origin_id")
    if origin_id:
        origin = db.query(ScrapingOrigin).filter(ScrapingOrigin.id == origin_id).first()
        if origin:
            origin_name = origin.name
    
    # Calculate duration
    duration_seconds = None
    start_time_str = job_data.get("started_at") or job_data.get("queued_at")
    end_time_str = job_data.get("completed_at") or job_data.get("failed_at")
    start_time = None
    end_time = None
    
    if start_time_str:
        try:
            start_time = datetime.fromisoformat(start_time_str.replace('Z', '+00:00'))
        except:
            pass
    
    if end_time_str:
        try:
            end_time = datetime.fromisoformat(end_time_str.replace('Z', '+00:00'))
            if start_time:
                duration_seconds = (end_time - start_time).total_seconds()
        except:
            pass
    
    # Determine trigger type
    trigger_type = "scheduler"
    if job_data.get("triggered_by"):
        if "realtime" in job_data.get("mode", "").lower():
            trigger_type = "realtime_fallback"
        else:
            trigger_type = "API"
    
    # Error breakdown (simple categorization)
    error_breakdown = {}
    error_summary = job_data.get("error", "")
    if error_summary:
        error_lower = error_summary.lower()
        if "timeout" in error_lower:
            error_breakdown["TIMEOUT"] = 1
        elif "http" in error_lower or "40" in error_summary or "50" in error_summary:
            error_breakdown["HTTP_ERROR"] = 1
        elif "network" in error_lower or "connection" in error_lower:
            error_breakdown["NETWORK_ERROR"] = 1
        elif "robots" in error_lower:
            error_breakdown["ROBOTS_DISALLOWED"] = 1
        else:
            error_breakdown["UNKNOWN"] = 1
    
    # Top errors (just the error message if present)
    top_errors = []
    if error_summary:
        top_errors = [error_summary]
    
    # Related documents
    related_documents = []
    document_id = job_data.get("document_id")
    if document_id:
        related_documents = [document_id]
    
    return JobDetailResponse(
        job_id=job_id,
        origin_id=origin_id,
        origin_name=origin_name,
        mode=job_data.get("mode", "unknown"),
        trigger_type=trigger_type,
        start_time=start_time or datetime.utcnow(),
        end_time=end_time,
        duration_seconds=duration_seconds,
        status=job_data.get("status", "unknown"),
        pages_attempted=job_data.get("pages_attempted", job_data.get("pages_crawled", 0)),
        pages_succeeded=job_data.get("pages_succeeded", job_data.get("pages_crawled", 0)),
        policy_relevant_pages=job_data.get("policy_relevant_pages", 0),
        new_docs_ingested=1 if document_id else 0,
        error_summary=error_summary,
        error_breakdown=error_breakdown,
        top_errors=top_errors,
        related_documents=related_documents
    )


@router.get("/documents", response_model=PaginatedResponse)
async def get_dashboard_documents(
    origin_id: Optional[int] = Query(None, description="Filter by origin ID"),
    source_type: Optional[str] = Query(None, description="Filter by source type"),
    date_from: Optional[str] = Query(None, description="Filter from date (ISO format)"),
    date_to: Optional[str] = Query(None, description="Filter to date (ISO format)"),
    relevance_flag: Optional[str] = Query(None, description="Filter by relevance (high/medium/low)"),
    has_duplicates: Optional[bool] = Query(None, description="Filter by duplicate status"),
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(20, ge=1, le=100, description="Items per page"),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_active_admin)
):
    """
    Get paginated list of documents with filters.
    
    Returns:
        PaginatedResponse with document summaries
    """
    # Build query
    query = db.query(Document)
    
    # Apply filters
    if origin_id:
        query = query.filter(Document.origin_id == origin_id)
    
    if date_from:
        try:
            date_from_dt = datetime.fromisoformat(date_from.replace('Z', '+00:00'))
            query = query.filter(Document.ingestion_date >= date_from_dt)
        except:
            pass
    
    if date_to:
        try:
            date_to_dt = datetime.fromisoformat(date_to.replace('Z', '+00:00'))
            query = query.filter(Document.ingestion_date <= date_to_dt)
        except:
            pass
    
    # Get total count before pagination
    total = query.count()
    
    # Apply pagination
    offset = (page - 1) * limit
    documents = query.order_by(Document.ingestion_date.desc()).offset(offset).limit(limit).all()
    
    # Build summaries with post-filtering (since source_type and relevance are in metadata)
    summaries = []
    for doc in documents:
        # Get origin name
        origin_name = None
        if doc.origin_id:
            origin = db.query(ScrapingOrigin).filter(ScrapingOrigin.id == doc.origin_id).first()
            if origin:
                origin_name = origin.name
        
        # Get chunk count
        chunks_count = db.query(Chunk).filter(Chunk.document_id == doc.id).count()
        
        # Parse metadata for source_type and relevance
        doc_source_type = "scheduled"
        relevance_flag_val = None
        if doc.document_metadata:
            try:
                meta = json.loads(doc.document_metadata)
                doc_source_type = meta.get("source_type", "scheduled")
                relevance_score = meta.get("relevance_score")
                if relevance_score is not None:
                    if relevance_score >= 5:
                        relevance_flag_val = "high"
                    elif relevance_score >= 3:
                        relevance_flag_val = "medium"
                    else:
                        relevance_flag_val = "low"
            except:
                pass
        
        # Apply source_type filter (extracted from metadata)
        if source_type and doc_source_type != source_type:
            continue
        
        # Apply relevance filter
        if relevance_flag and relevance_flag_val != relevance_flag:
            continue
        
        # Check for duplicates (simple: same URL and origin)
        dedup_status = "unique"
        if doc.url and doc.origin_id:
            dup_count = db.query(Document).filter(
                Document.url == doc.url,
                Document.origin_id == doc.origin_id,
                Document.id != doc.id
            ).count()
            if dup_count > 0:
                dedup_status = f"duplicate"
        
        # Apply duplicate filter
        if has_duplicates is not None:
            is_dup = dedup_status == "duplicate"
            if has_duplicates != is_dup:
                continue
        
        summaries.append({
            "id": doc.id,
            "title": doc.title,
            "origin_id": doc.origin_id,
            "origin_name": origin_name,
            "url": doc.url,
            "source_type": doc_source_type,
            "version": None,  # Future: version tracking
            "last_modified": None,  # Future: last_modified tracking
            "ingestion_date": doc.ingestion_date.isoformat() if doc.ingestion_date else None,
            "chunks_count": chunks_count,
            "relevance_flag": relevance_flag_val,
            "dedup_status": dedup_status
        })
    
    # Recalculate total after post-filtering
    total_filtered = len(summaries)
    
    return PaginatedResponse(
        items=summaries,
        total=total_filtered,
        page=page,
        limit=limit,
        pages=(total_filtered + limit - 1) // limit if total_filtered > 0 else 0
    )


@router.get("/documents/{document_id}", response_model=DocumentDetailResponse)
async def get_dashboard_document_detail(
    document_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_active_admin)
):
    """
    Get detailed information about a specific document.
    
    Returns:
        DocumentDetailResponse with metadata and chunks summary
    """
    doc = db.query(Document).filter(Document.id == document_id).first()
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found"
        )
    
    # Get origin name
    origin_name = None
    if doc.origin_id:
        origin = db.query(ScrapingOrigin).filter(ScrapingOrigin.id == doc.origin_id).first()
        if origin:
            origin_name = origin.name
    
    # Get chunks
    chunks = db.query(Chunk).filter(Chunk.document_id == document_id).order_by(Chunk.chunk_index).all()
    chunks_count = len(chunks)
    
    # Build chunks summary
    chunks_summary = []
    for chunk in chunks:
        chunks_summary.append({
            "id": chunk.id,
            "chunk_index": chunk.chunk_index,
            "content_preview": chunk.content[:200] + "..." if len(chunk.content) > 200 else chunk.content,
            "embedding_id": chunk.embedding_id
        })
    
    # Parse metadata
    metadata = None
    if doc.document_metadata:
        try:
            metadata = json.loads(doc.document_metadata)
        except:
            pass
    
    # Version history (future: implement versioning)
    version_history = []
    
    return DocumentDetailResponse(
        id=doc.id,
        title=doc.title,
        source=doc.source,
        url=doc.url,
        origin_id=doc.origin_id,
        origin_name=origin_name,
        ingestion_date=doc.ingestion_date,
        chunks_count=chunks_count,
        metadata=metadata,
        chunks_summary=chunks_summary,
        version_history=version_history
    )


@router.get("/settings", response_model=SettingsResponse)
async def get_dashboard_settings(
    current_user = Depends(get_current_active_admin)
):
    """
    Get current global settings for dashboard configuration.
    
    Returns:
        SettingsResponse with all configurable settings
    """
    return SettingsResponse(
        crawling={
            "priority_score_threshold": getattr(settings, 'priority_score_threshold', -10.0),
            "max_low_priority_pages": getattr(settings, 'max_low_priority_pages', 10),
            "sitemap_max_urls_per_origin": getattr(settings, 'sitemap_max_urls_per_origin', None) or 1000,
            "enable_priority_queue": getattr(settings, 'enable_priority_queue', False),
            "enable_topic_filtering": getattr(settings, 'enable_topic_filtering', False),
            "policy_keyword_threshold": getattr(settings, 'policy_keyword_threshold', 3)
        },
        realtime_web={
            "enable_realtime_web": getattr(settings, 'enable_realtime_web', False),
            "realtime_web_max_seconds": getattr(settings, 'realtime_web_max_seconds', 5.0),
            "realtime_web_max_pages": getattr(settings, 'realtime_web_max_pages', 10),
            "realtime_web_max_bytes_per_page": getattr(settings, 'realtime_web_max_bytes_per_page', None) or 500000,
            "min_similarity_threshold": getattr(settings, 'min_similarity_threshold', 0.6),
            "min_results": getattr(settings, 'min_results', 3)
        },
        rag={
            "rag_mode": "semantic_only",  # Default, future: add to config
            "enable_hybrid_search": getattr(settings, 'enable_hybrid_search', False),
            "enable_reranking": getattr(settings, 'enable_reranking', False)
        },
        data_retention={
            "scheduled_docs_retention": "keep_all",  # Future: implement
            "realtime_web_ttl_hours": getattr(settings, 'web_cache_ttl_hours', None) or 24,
            "enable_deduplication": False  # Future: implement
        }
    )


@router.patch("/settings", response_model=SettingsResponse)
async def update_dashboard_settings(
    settings_update: SettingsUpdate,
    current_user = Depends(get_current_active_admin)
):
    """
    Update safe global settings.
    
    Note: This updates in-memory settings. For production, persist to database or config file.
    """
    # Update crawling settings
    if settings_update.crawling:
        for key, value in settings_update.crawling.items():
            if hasattr(settings, key):
                # Validate value
                if key == "priority_score_threshold" and not isinstance(value, (int, float)):
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Invalid value for {key}: must be a number"
                    )
                if key == "max_low_priority_pages" and (not isinstance(value, int) or value < 0):
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Invalid value for {key}: must be a non-negative integer"
                    )
                setattr(settings, key, value)
    
    # Update realtime_web settings
    if settings_update.realtime_web:
        for key, value in settings_update.realtime_web.items():
            if hasattr(settings, key):
                # Validate value
                if "max_seconds" in key and (not isinstance(value, (int, float)) or value <= 0):
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Invalid value for {key}: must be a positive number"
                    )
                if "max_pages" in key and (not isinstance(value, int) or value < 1):
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Invalid value for {key}: must be a positive integer"
                    )
                setattr(settings, key, value)
    
    # Update RAG settings (future: add to config)
    # For now, these are placeholders
    
    # Update data retention settings (future: implement)
    
    # Return updated settings
    return await get_dashboard_settings(current_user)

