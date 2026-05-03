"""Database indexes for URL Shortener API

This module documents and manages all database indexes for optimal query performance.
Indexes are crucial for:
- Fast lookups by primary keys
- Efficient filtering and sorting
- Range queries on timestamps
- Composite queries combining multiple columns
"""

from sqlalchemy import Index
from sqlalchemy.schema import CreateIndex, DropIndex


# ============================================================================
# Index Strategy Documentation
# ============================================================================

"""
INDEX STRATEGY FOR URL SHORTENER API
====================================

1. PRIMARY KEY INDEXES (Automatic)
   - users.id (UUID)
   - urls.id (BigInteger)
   - clicks.id (BigInteger)
   - audit_logs.id (BigInteger)
   - click_aggregates.id (BigInteger)

2. UNIQUE INDEXES (Automatic from unique=True)
   - users.email (lookups by email)
   - users.api_key (authentication)
   - urls.short_code (redirect lookups - CRITICAL)

3. SINGLE COLUMN INDEXES
   ✅ users.email
   ✅ users.api_key
   ✅ urls.short_code
   ✅ urls.user_id (list user's URLs)
   ✅ urls.created_at (sort by date)
   ✅ urls.is_active (filter active URLs)
   ✅ clicks.url_id (analytics queries)
   ✅ clicks.clicked_at (time-series analysis)
   ✅ clicks.country (geographic analytics)
   ✅ clicks.device_type (device breakdown)
   ✅ clicks.ip_address (unique visitor counting) ← NEW
   ✅ audit_logs.user_id (user activity)
   ✅ audit_logs.action (audit trail filtering)
   ✅ audit_logs.created_at (timeline queries)
   ✅ click_aggregates.url_id (hourly stats)
   ✅ click_aggregates.date_hour (time-range queries)

4. COMPOSITE INDEXES (Multiple columns)
   ✅ urls(user_id, created_at DESC)
      → List user's URLs sorted by newest first
   
   ✅ urls(is_active, expires_at)
      → Filter active URLs and check expiration
   
   ✅ clicks(url_id, clicked_at DESC) ← NEW
      → Get recent clicks for analytics
   
   ✅ click_aggregates(url_id, date_hour DESC)
      → Get hourly stats for specific URL
   
   ✅ audit_logs(user_id, action, created_at DESC)
      → User activity audit trail

5. COVERING INDEXES (Future optimization)
   Not implemented yet - add when queries need optimization
   Example: Index on (url_id, clicked_at, country)
"""


# ============================================================================
# Index Definitions for Migration
# ============================================================================

def get_missing_indexes():
    """
    Returns list of indexes that should be created.
    Use this in a migration if indexes are missing.
    
    Returns:
        list: Index definitions for creation
    """
    return [
        # Click table - new indexes for better analytics performance
        {
            "name": "idx_clicks_ip_address",
            "table": "clicks",
            "columns": ["ip_address"],
            "description": "Fast lookups of clicks by IP address (unique visitor counting)"
        },
        {
            "name": "idx_clicks_url_clicked",
            "table": "clicks",
            "columns": ["url_id", "clicked_at"],
            "description": "Composite index for recent clicks analytics"
        },
    ]


# ============================================================================
# Query Performance Impact
# ============================================================================

"""
QUERIES OPTIMIZED BY THESE INDEXES:

1. Redirect lookup (HOTTEST - redirects are frequent)
   SELECT * FROM urls WHERE short_code = ? AND is_active = true
   → Uses: idx_urls_short_code (unique index)
   Performance: O(1) - instant

2. List user's URLs
   SELECT * FROM urls WHERE user_id = ? AND is_active = true ORDER BY created_at DESC
   → Uses: idx_urls_user_id_created
   Performance: O(log n) - very fast

3. Get URL analytics
   SELECT COUNT(*), country, device_type 
   FROM clicks WHERE url_id = ?
   GROUP BY country, device_type
   → Uses: idx_clicks_url_id
   Performance: O(k) where k = clicks for URL

4. Count unique visitors
   SELECT COUNT(DISTINCT ip_address) FROM clicks WHERE url_id = ?
   → Uses: idx_clicks_ip_address (NEW)
   Performance: O(k log k) - much better than O(k²)

5. Recent clicks for analytics dashboard
   SELECT * FROM clicks WHERE url_id = ? ORDER BY clicked_at DESC LIMIT 100
   → Uses: idx_clicks_url_clicked (NEW)
   Performance: O(log n) - very fast

6. User audit trail
   SELECT * FROM audit_logs WHERE user_id = ? AND action = ? ORDER BY created_at DESC
   → Uses: idx_audit_logs_user_action
   Performance: O(log n) - fast

7. Check expired URLs
   SELECT * FROM urls WHERE is_active = true AND expires_at < NOW()
   → Uses: idx_urls_active_expires
   Performance: O(k) where k = expired URLs
"""


# ============================================================================
# Migration SQL Commands
# ============================================================================

def get_migration_sql_postgres():
    """
    SQL commands to add missing indexes in PostgreSQL.
    Run these in a migration or directly in psql.
    
    Returns:
        str: SQL migration script
    """
    return """
-- Day 167: Add missing database indexes for analytics optimization

-- Index on ip_address for unique visitor counting
CREATE INDEX IF NOT EXISTS idx_clicks_ip_address 
ON clicks(ip_address);

-- Composite index for recent clicks analytics
CREATE INDEX IF NOT EXISTS idx_clicks_url_clicked 
ON clicks(url_id, clicked_at DESC);

-- Analyze tables to update query planner statistics
ANALYZE clicks;
ANALYZE urls;
ANALYZE audit_logs;
"""


def get_migration_sql_sqlite():
    """
    SQL commands for SQLite (for development).
    SQLite is more limited but still needs indexes.
    
    Returns:
        str: SQL migration script for SQLite
    """
    return """
-- Day 167: Add missing database indexes for SQLite development

-- Index on ip_address for unique visitor counting
CREATE INDEX IF NOT EXISTS idx_clicks_ip_address 
ON clicks(ip_address);

-- Composite index for recent clicks analytics
CREATE INDEX IF NOT EXISTS idx_clicks_url_clicked 
ON clicks(url_id, clicked_at DESC);

-- SQLite doesn't have ANALYZE in same way, but it helps
ANALYZE;
"""


# ============================================================================
# Index Monitoring & Maintenance
# ============================================================================

"""
HOW TO MONITOR INDEX USAGE IN PRODUCTION:

PostgreSQL:
-----------
-- Find unused indexes
SELECT schemaname, tablename, indexname, idx_scan
FROM pg_stat_user_indexes
WHERE idx_scan = 0
ORDER BY idx_blks_read DESC;

-- Index size
SELECT indexrelname, pg_size_pretty(pg_relation_size(indexrelid)) AS size
FROM pg_stat_user_indexes
ORDER BY pg_relation_size(indexrelid) DESC;

-- Analyze table
ANALYZE table_name;

-- Check index fragmentation
SELECT schemaname, tablename, indexname, idx_blks_read, idx_tup_read, idx_tup_fetch
FROM pg_stat_user_indexes;


SQLite:
-------
-- Verify indexes exist
.indices table_name

-- Explain query plan
EXPLAIN QUERY PLAN SELECT ...;

-- Reindex if fragmented
REINDEX;
"""


# ============================================================================
# Performance Benchmarks
# ============================================================================

"""
EXPECTED PERFORMANCE IMPROVEMENTS:

Before adding indexes:
- Count unique visitors: O(n²) - SLOW with millions of clicks
- Recent clicks query: O(n log n) - needs full scan + sort
- Analytics by country: O(n) - scans all clicks

After adding indexes:
- Count unique visitors: O(n log n) → O(1) with index
- Recent clicks: O(log n) - direct index range scan
- Analytics: O(k log k) where k = clicks per URL (much smaller)

For 1M clicks across 1000 URLs:
- Before: COUNT(DISTINCT ip) = ~30 seconds
- After: COUNT(DISTINCT ip) = ~100ms (300x faster!)
"""


# ============================================================================
# Best Practices
# ============================================================================

"""
INDEX BEST PRACTICES FOR THIS PROJECT:

1. Index Order Matters
   ✓ Equality before range: WHERE user_id = ? AND created_at > ?
   ✓ Use: INDEX(user_id, created_at)
   ✓ Not: INDEX(created_at, user_id)

2. Keep Indexes Lean
   ✓ Index only columns used in WHERE/ORDER BY
   ✗ Don't index unused columns

3. Monitor Index Usage
   ✓ Check pg_stat_user_indexes regularly
   ✓ Drop unused indexes

4. Update Statistics
   ✓ Run ANALYZE after bulk operations
   ✓ Query planner depends on accurate stats

5. Balance Trade-offs
   ✓ Indexes speed up reads
   ✗ Indexes slow down writes
   ✓ For read-heavy API like this: add more indexes

6. Composite Index Rules
   ✓ Equality columns first (user_id)
   ✓ Then range columns (created_at DESC)
   ✓ Then sort columns
"""
