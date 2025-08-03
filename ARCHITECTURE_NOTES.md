# Architecture Notes

## Database Setup

### Current State
- `alembic.ini` is configured but Alembic hasn't been initialized
- Using SQLite for development/testing
- PostgreSQL configuration ready for production

### To Initialize Alembic (when needed):
```bash
# Initialize Alembic
alembic init alembic

# Create first migration
alembic revision --autogenerate -m "Initial schema"

# Apply migrations
alembic upgrade head
```

## Directory Structure Clarification

### Actual API Location
- ✅ `src/api/` - Contains all API code
  - `server.py` - FastAPI application
  - `routes.py` - Route definitions
- ❌ `/api/` - Empty folder (can be removed)

### Scripts Organization
- ✅ `src/scrapers/run.py` - Main scraper runner
- ✅ `src/cli.py` - CLI interface
- ❌ `/scripts/` - Empty folder (reserved for future utilities)

### Future Scripts (to be added to `/scripts/`):
1. `validate_models.py` - Validate all model documentation
2. `bulk_update.py` - Update multiple models at once  
3. `export_practices.py` - Export to different formats
4. `cleanup_old_data.py` - Remove outdated practices
5. `generate_report.py` - Generate usage statistics

## Why This Structure?

1. **Separation of Concerns**
   - `/src/` - Core application code
   - `/scripts/` - Standalone maintenance scripts
   - `/models/` - Data files (best practices)

2. **Scalability**
   - Database migrations ready when needed
   - Script folder ready for operational tools
   - Clear separation between app and utilities

## Cleanup Recommendations

1. Remove empty `/api/` folder (use `src/api/` instead)
2. Keep `/scripts/` for future maintenance scripts
3. Initialize Alembic when moving to PostgreSQL
4. Consider moving `test_system.py` to `/scripts/`