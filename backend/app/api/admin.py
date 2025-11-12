from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.models.database import get_db, ScrapingOrigin
from app.models.schemas import (
    ScrapingOriginCreate,
    ScrapingOriginUpdate,
    ScrapingOriginResponse,
    SystemHealth,
    OriginStatus
)
from app.core.security import get_current_active_admin

router = APIRouter()


@router.get("/origins", response_model=List[ScrapingOriginResponse])
async def list_origins(
    db: Session = Depends(get_db),
    current_user = Depends(get_current_active_admin)
):
    """List all scraping origins"""
    origins = db.query(ScrapingOrigin).all()
    return origins


@router.post("/origins", response_model=ScrapingOriginResponse, status_code=status.HTTP_201_CREATED)
async def create_origin(
    origin: ScrapingOriginCreate,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_active_admin)
):
    """Create a new scraping origin"""
    db_origin = ScrapingOrigin(**origin.dict())
    db.add(db_origin)
    db.commit()
    db.refresh(db_origin)
    return db_origin


@router.put("/origins/{origin_id}", response_model=ScrapingOriginResponse)
async def update_origin(
    origin_id: int,
    origin_update: ScrapingOriginUpdate,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_active_admin)
):
    """Update a scraping origin"""
    db_origin = db.query(ScrapingOrigin).filter(ScrapingOrigin.id == origin_id).first()
    if not db_origin:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Origin not found"
        )
    
    update_data = origin_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_origin, field, value)
    
    db.commit()
    db.refresh(db_origin)
    return db_origin


@router.delete("/origins/{origin_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_origin(
    origin_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_active_admin)
):
    """Delete a scraping origin"""
    db_origin = db.query(ScrapingOrigin).filter(ScrapingOrigin.id == origin_id).first()
    if not db_origin:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Origin not found"
        )
    
    db.delete(db_origin)
    db.commit()
    return None


@router.get("/origins/{origin_id}/status", response_model=dict)
async def get_origin_status(
    origin_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_active_admin)
):
    """Get status information for a specific origin"""
    from app.services.scraping_service import scraping_service
    status_info = scraping_service.get_origin_status(db, origin_id)
    if not status_info:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Origin not found"
        )
    return status_info


@router.get("/health", response_model=SystemHealth)
async def get_system_health(
    db: Session = Depends(get_db),
    current_user = Depends(get_current_active_admin)
):
    """Get system health status"""
    origins = db.query(ScrapingOrigin).all()
    origin_statuses = [
        OriginStatus(
            origin_id=origin.id,
            origin_name=origin.name,
            last_run=origin.last_run,
            last_status=origin.last_status,
            enabled=origin.enabled
        )
        for origin in origins
    ]
    
    return SystemHealth(
        status="healthy",
        origins=origin_statuses
    )

