"""
Database migration script to add enhanced metadata fields to ScrapingOrigin table.

This script adds the following fields (all nullable for backward compatibility):
- country_code: String (ISO country codes)
- topic_tags: Text (JSON array of topic tags)
- crawl_priority: Integer (1-10 scale, default: 5)
- allowed_path_patterns: Text (JSON array of regex patterns)
- excluded_path_patterns: Text (JSON array of regex patterns)
- sitemap_url: String (optional sitemap URL)

Run this script after deploying the updated database model.
"""
import logging
import sys
from sqlalchemy import text
from app.models.database import engine, SessionLocal

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def migrate_origin_metadata():
    """
    Add enhanced metadata columns to scraping_origins table.
    All columns are nullable to maintain backward compatibility.
    """
    db = SessionLocal()
    try:
        logger.info("Starting migration: Adding enhanced metadata fields to scraping_origins table")
        
        # Check if columns already exist (idempotent migration)
        inspector = db.execute(text("PRAGMA table_info(scraping_origins)"))
        existing_columns = [row[1] for row in inspector.fetchall()]
        
        new_columns = {
            'country_code': 'VARCHAR',
            'topic_tags': 'TEXT',
            'crawl_priority': 'INTEGER',
            'allowed_path_patterns': 'TEXT',
            'excluded_path_patterns': 'TEXT',
            'sitemap_url': 'VARCHAR'
        }
        
        for column_name, column_type in new_columns.items():
            if column_name not in existing_columns:
                if 'sqlite' in str(engine.url):
                    # SQLite syntax
                    if column_name == 'crawl_priority':
                        # Set default value for crawl_priority
                        db.execute(text(
                            f"ALTER TABLE scraping_origins ADD COLUMN {column_name} {column_type} DEFAULT 5"
                        ))
                    else:
                        db.execute(text(
                            f"ALTER TABLE scraping_origins ADD COLUMN {column_name} {column_type}"
                        ))
                else:
                    # PostgreSQL syntax
                    if column_name == 'crawl_priority':
                        db.execute(text(
                            f"ALTER TABLE scraping_origins ADD COLUMN {column_name} {column_type} DEFAULT 5"
                        ))
                    else:
                        db.execute(text(
                            f"ALTER TABLE scraping_origins ADD COLUMN {column_name} {column_type}"
                        ))
                logger.info(f"Added column: {column_name}")
            else:
                logger.info(f"Column {column_name} already exists, skipping")
        
        db.commit()
        logger.info("Migration completed successfully")
        
    except Exception as e:
        logger.error(f"Migration failed: {e}")
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    try:
        migrate_origin_metadata()
        logger.info("Migration script completed successfully")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Migration script failed: {e}")
        sys.exit(1)

