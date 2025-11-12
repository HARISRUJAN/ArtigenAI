from datetime import datetime
from typing import Optional
from sqlalchemy.orm import Session
from app.models.database import ScrapingOrigin

class ScrapingService:
    def update_origin_status(
        self,
        db: Session,
        origin_id: int,
        status: str  # "success" or "failed"
    ):
        """Update the last run status of an origin"""
        origin = db.query(ScrapingOrigin).filter(ScrapingOrigin.id == origin_id).first()
        if origin:
            origin.last_run = datetime.utcnow()
            origin.last_status = status
            db.commit()
    
    def get_origin_status(self, db: Session, origin_id: int) -> Optional[dict]:
        """Get status information for an origin"""
        origin = db.query(ScrapingOrigin).filter(ScrapingOrigin.id == origin_id).first()
        if not origin:
            return None
        
        return {
            "id": origin.id,
            "name": origin.name,
            "last_run": origin.last_run,
            "last_status": origin.last_status,
            "enabled": origin.enabled
        }


scraping_service = ScrapingService()

