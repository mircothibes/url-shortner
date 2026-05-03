"""Database migrations for URL Shortener API

This module provides manual migration functions to add/remove database indexes.
Run these functions directly in Python or via CLI.

Usage:
    from app.migrations import run_all_migrations
    run_all_migrations()
"""

import os
from sqlalchemy import text, inspect
from app.database import engine
from app.models import Base


# ============================================================================
# Migration Functions
# ============================================================================

def create_missing_indexes():
    """
    Create missing indexes for analytics optimization.
    Safe to run multiple times - uses IF NOT EXISTS.
    
    Indexes added:
    - idx_clicks_ip_address: For unique visitor counting
    - idx_clicks_url_clicked: For recent clicks analytics
    """
    from app.database import SessionLocal
    
    migrations = [
        {
            "name": "idx_clicks_ip_address",
            "sql": "CREATE INDEX IF NOT EXISTS idx_clicks_ip_address ON clicks(ip_address);",
            "description": "Index on ip_address for unique visitor counting"
        },
        {
            "name": "idx_clicks_url_clicked",
            "sql": "CREATE INDEX IF NOT EXISTS idx_clicks_url_clicked ON clicks(url_id, clicked_at DESC);",
            "description": "Composite index for recent clicks analytics"
        },
    ]
    
    db = SessionLocal()
    try:
        for migration in migrations:
            try:
                print(f"Creating index: {migration['name']}")
                print(f"  Description: {migration['description']}")
                db.execute(text(migration['sql']))
                db.commit()
                print(f"  ✅ Success\n")
            except Exception as e:
                print(f"  ❌ Error: {str(e)}\n")
                db.rollback()
    finally:
        db.close()


def analyze_tables():
    """
    Run ANALYZE on tables to update query planner statistics.
    Should be run after bulk operations or index creation.
    
    Tables analyzed:
    - users
    - urls
    - clicks
    - click_aggregates
    - audit_logs
    """
    from app.database import SessionLocal
    
    tables = ["users", "urls", "clicks", "click_aggregates", "audit_logs"]
    
    db = SessionLocal()
    try:
        for table in tables:
            try:
                print(f"Analyzing table: {table}")
                db.execute(text(f"ANALYZE {table};"))
                db.commit()
                print(f"  ✅ Success\n")
            except Exception as e:
                print(f"  ❌ Error: {str(e)}\n")
                db.rollback()
    finally:
        db.close()


def list_indexes():
    """
    List all indexes on relevant tables.
    Useful for verifying migrations ran successfully.
    
    Returns:
        dict: Indexes grouped by table name
    """
    inspector = inspect(engine)
    tables = ["users", "urls", "clicks", "click_aggregates", "audit_logs"]
    
    indexes_info = {}
    
    print("\n" + "="*80)
    print("DATABASE INDEXES STATUS")
    print("="*80 + "\n")
    
    with engine.connect() as connection:
        for table in tables:
            print(f"Table: {table}")
            print("-" * 80)
            
            # Get indexes from inspector
            indexes = inspector.get_indexes(table)
            
            if not indexes:
                print("  No indexes found\n")
                continue
            
            for idx in indexes:
                print(f"  Index: {idx['name']}")
                print(f"    Columns: {', '.join(idx['column_names'])}")
                print(f"    Unique: {idx['unique']}")
                print()
            
            indexes_info[table] = indexes
    
    return indexes_info


def get_index_sizes():
    """
    Get size of each index in MB.
    PostgreSQL only.
    
    Returns:
        dict: Index names and their sizes
    """
    sql = """
    SELECT 
        indexrelname,
        pg_size_pretty(pg_relation_size(indexrelid)) AS size
    FROM pg_stat_user_indexes
    ORDER BY pg_relation_size(indexrelid) DESC;
    """
    
    try:
        with engine.connect() as connection:
            result = connection.execute(text(sql))
            
            print("\n" + "="*80)
            print("INDEX SIZES")
            print("="*80 + "\n")
            
            index_sizes = {}
            for row in result:
                print(f"  {row[0]}: {row[1]}")
                index_sizes[row[0]] = row[1]
            
            print()
            return index_sizes
    except Exception as e:
        print(f"Could not get index sizes: {str(e)}")
        print("(This is normal on SQLite - PostgreSQL only feature)\n")
        return {}


def get_index_usage():
    """
    Get usage statistics for indexes.
    PostgreSQL only.
    
    Returns:
        dict: Index usage information
    """
    sql = """
    SELECT 
        indexrelname,
        idx_scan,
        idx_tup_read,
        idx_tup_fetch
    FROM pg_stat_user_indexes
    ORDER BY idx_scan DESC;
    """
    
    try:
        with engine.connect() as connection:
            result = connection.execute(text(sql))
            
            print("\n" + "="*80)
            print("INDEX USAGE STATISTICS")
            print("="*80 + "\n")
            
            usage_info = {}
            for row in result:
                print(f"  {row[0]}")
                print(f"    Scans: {row[1]}")
                print(f"    Tuples read: {row[2]}")
                print(f"    Tuples fetched: {row[3]}")
                print()
                usage_info[row[0]] = {
                    "scans": row[1],
                    "tuples_read": row[2],
                    "tuples_fetched": row[3]
                }
            
            return usage_info
    except Exception as e:
        print(f"Could not get index usage: {str(e)}")
        print("(This is normal on SQLite - PostgreSQL only feature)\n")
        return {}


def run_all_migrations():
    """
    Run all migrations in sequence.
    Safe to run multiple times.
    
    Flow:
    1. Create tables if they don't exist
    2. Create missing indexes
    3. Analyze tables for query planner
    4. Display index status
    """
    print("\n" + "="*80)
    print("STARTING DATABASE MIGRATIONS - DAY 167")
    print("="*80 + "\n")
    
    # Step 1: Ensure tables exist
    print("Step 1: Creating tables (if needed)...")
    print("-" * 80)
    try:
        Base.metadata.create_all(bind=engine)
        print("✅ Tables verified/created\n")
    except Exception as e:
        print(f"❌ Error: {str(e)}\n")
        return False
    
    # Step 2: Create missing indexes
    print("Step 2: Creating missing indexes...")
    print("-" * 80)
    create_missing_indexes()
    
    # Step 3: Analyze tables
    print("Step 3: Analyzing tables for query planner...")
    print("-" * 80)
    analyze_tables()
    
    # Step 4: Display status
    print("Step 4: Verifying migration status...")
    print("-" * 80)
    list_indexes()
    
    # Step 5: Show sizes (if PostgreSQL)
    get_index_sizes()
    
    # Step 6: Show usage (if PostgreSQL)
    get_index_usage()
    
    print("="*80)
    print("MIGRATION COMPLETE")
    print("="*80 + "\n")
    
    return True


# ============================================================================
# CLI Entry Point
# ============================================================================

if __name__ == "__main__":
    """
    Run migrations from command line:
    
    python app/migrations.py
    """
    import sys
    
    if len(sys.argv) > 1:
        command = sys.argv[1].lower()
        
        if command == "create-indexes":
            create_missing_indexes()
        elif command == "analyze":
            analyze_tables()
        elif command == "list":
            list_indexes()
        elif command == "sizes":
            get_index_sizes()
        elif command == "usage":
            get_index_usage()
        elif command == "all":
            run_all_migrations()
        else:
            print(f"Unknown command: {command}")
            print("\nAvailable commands:")
            print("  python app/migrations.py create-indexes")
            print("  python app/migrations.py analyze")
            print("  python app/migrations.py list")
            print("  python app/migrations.py sizes")
            print("  python app/migrations.py usage")
            print("  python app/migrations.py all")
    else:
        # Default: run all migrations
        run_all_migrations()
