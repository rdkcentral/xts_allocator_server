#!/usr/bin/env python3
"""Database migration script for Phase 3 features.

Creates test_executions table for test lifecycle tracking.
"""

from sqlalchemy import inspect
from models import engine, SessionLocal, TestExecution

def migrate():
    """Run migration to add Phase 3 tables."""
    session = SessionLocal()
    
    try:
        print("Starting Phase 3 migration...")
        
        # Check if tables exist
        inspector = inspect(engine)
        existing_tables = inspector.get_table_names()
        
        print(f"Found tables: {existing_tables}")
        
        # Create test_executions table if it doesn't exist
        if 'test_executions' not in existing_tables:
            print("Creating test_executions table...")
            TestExecution.__table__.create(engine)
            print("  ✓ test_executions table created")
        else:
            print("  ⊙ test_executions table already exists")
        
        session.commit()
        print("✅ Phase 3 migration completed successfully!")
        
    except Exception as e:
        session.rollback()
        print(f"❌ Migration failed: {e}")
        raise
    finally:
        session.close()

if __name__ == "__main__":
    migrate()
