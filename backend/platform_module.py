"""
PLATFORM MODULE
Owns deployment configuration, health checks, and environment setup.

Boundaries:
- Deployment: Render configuration, health endpoints
- Environment: Env var validation, connection pooling
- Monitoring: Health checks, basic observability
"""
import os
import logging
from contextlib import contextmanager

import psycopg
from psycopg.rows import dict_row
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Load environment variables
load_dotenv()

# Configure logger
logger = logging.getLogger("uvicorn.error")


# ======================================================================
# CONFIG
# ======================================================================

DATABASE_URL = os.getenv("DATABASE_URL")
ADMIN_TOKEN = os.getenv("ADMIN_TOKEN", "dev-admin-token-12345")


# ======================================================================
# DEPENDENCIES
# ======================================================================

@contextmanager
def get_db():
    """Context manager for database connections"""
    conn = psycopg.connect(DATABASE_URL, row_factory=dict_row)
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def count_studies() -> int:
    """Count total published studies in database"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) as count FROM studies WHERE is_published = TRUE")
        return cursor.fetchone()['count']


# ======================================================================
# CORS CONFIGURATION
# ======================================================================

def get_allowed_origins() -> list[str]:
    """Get list of allowed CORS origins from environment"""
    origins = [
        "http://localhost:5173",
        "http://localhost:5174",
        "http://localhost:3000",
    ]
    extra_origins = os.getenv("FRONTEND_ORIGINS")
    if extra_origins:
        origins.extend([origin.strip() for origin in extra_origins.split(",") if origin.strip()])
    return origins


def configure_cors(app: FastAPI):
    """Add CORS middleware to FastAPI app"""
    app.add_middleware(
        CORSMiddleware,
        allow_origins=get_allowed_origins(),
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )


# ======================================================================
# ROUTES
# ======================================================================

def register_health_route(app: FastAPI):
    """Register health check endpoint"""

    @app.get("/health")
    def health_check():
        """Health check endpoint"""
        return {"status": "healthy", "total_studies": count_studies(), "database": "supabase-postgres"}


# ======================================================================
# STARTUP
# ======================================================================

def register_startup_handler(app: FastAPI):
    """Register startup event handler"""

    @app.on_event("startup")
    def startup_event():
        """Initialize application on startup"""
        print("Connecting to Supabase Postgres...")
        print(f"Database URL: {DATABASE_URL.split('@')[1] if '@' in DATABASE_URL else 'localhost'}")

        # Test database connection
        try:
            with get_db() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT COUNT(*) as count FROM studies WHERE is_published = TRUE")
                count = cursor.fetchone()['count']
                print(f"Successfully connected! Found {count} published studies in database.")
        except Exception as e:
            print(f"Warning: Could not connect to database: {e}")
            print("Make sure Supabase is running: supabase start")

        print("Application ready.")
