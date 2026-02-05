#!/usr/bin/env python3
"""Database migration script for Phase 2 features.

Adds new columns to existing tables:
- Device: allocation_type, last_seen, connectivity_status, system_metrics
- AllocationHistory: allocation_type, test_execution_count, total_test_time, idle_time
- Creates new Server table for federation
"""

from sqlalchemy import text, inspect
from models import engine, SessionLocal, Base, Server

def migrate():
    """Run migration to add Phase 2 columns."""
    session = SessionLocal()
    
    try:
        print("Starting Phase 2 migration...")
        
        # Check if tables exist
        inspector = inspect(engine)
        existing_tables = inspector.get_table_names()
        
        print(f"Found tables: {existing_tables}")
        
        if 'devices' in existing_tables:
            # Check which columns exist
            columns = [col['name'] for col in inspector.get_columns('devices')]
            print(f"Device columns: {columns}")
            
            # Add columns to devices table (SQLite doesn't support IF NOT EXISTS cleanly)
            print("Adding columns to devices table...")
            
            if 'allocation_type' not in columns:
                session.execute(text("ALTER TABLE devices ADD COLUMN allocation_type VARCHAR DEFAULT 'temporary' NOT NULL"))
                print("  ✓ allocation_type added")
            else:
                print("  ⊙ allocation_type already exists")
            
            if 'last_seen' not in columns:
                session.execute(text("ALTER TABLE devices ADD COLUMN last_seen DATETIME"))
                print("  ✓ last_seen added")
            else:
                print("  ⊙ last_seen already exists")
            
            if 'connectivity_status' not in columns:
                session.execute(text("ALTER TABLE devices ADD COLUMN connectivity_status VARCHAR"))
                print("  ✓ connectivity_status added")
            else:
                print("  ⊙ connectivity_status already exists")
            
            if 'system_metrics' not in columns:
                session.execute(text("ALTER TABLE devices ADD COLUMN system_metrics JSON"))
                print("  ✓ system_metrics added")
            else:
                print("  ⊙ system_metrics already exists")
        
        if 'allocation_history' in existing_tables:
            # Check which columns exist
            columns = [col['name'] for col in inspector.get_columns('allocation_history')]
            print(f"AllocationHistory columns: {columns}")
            
            # Add columns to allocation_history table
            print("Adding columns to allocation_history table...")
            
            if 'allocation_type' not in columns:
                session.execute(text("ALTER TABLE allocation_history ADD COLUMN allocation_type VARCHAR DEFAULT 'temporary'"))
                print("  ✓ allocation_type added")
            else:
                print("  ⊙ allocation_type already exists")
            
            if 'test_execution_count' not in columns:
                session.execute(text("ALTER TABLE allocation_history ADD COLUMN test_execution_count INTEGER DEFAULT 0"))
                print("  ✓ test_execution_count added")
            else:
                print("  ⊙ test_execution_count already exists")
            
            if 'total_test_time' not in columns:
                session.execute(text("ALTER TABLE allocation_history ADD COLUMN total_test_time INTEGER DEFAULT 0"))
                print("  ✓ total_test_time added")
            else:
                print("  ⊙ total_test_time already exists")
            
            if 'idle_time' not in columns:
                session.execute(text("ALTER TABLE allocation_history ADD COLUMN idle_time INTEGER DEFAULT 0"))
                print("  ✓ idle_time added")
            else:
                print("  ⊙ idle_time already exists")
        
        # Create servers table if it doesn't exist
        if 'servers' not in existing_tables:
            print("Creating servers table...")
            Server.__table__.create(engine)
            print("  ✓ servers table created")
        else:
            print("  ⊙ servers table already exists")
        
        session.commit()
        print("✅ Phase 2 migration completed successfully!")
        
    except Exception as e:
        session.rollback()
        print(f"❌ Migration failed: {e}")
        raise
    finally:
        session.close()

if __name__ == "__main__":
    migrate()
