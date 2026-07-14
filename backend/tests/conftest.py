"""Sets required env vars before app.main is imported by any test module."""
import os

os.environ.setdefault("ENVIRONMENT", "development")
os.environ.setdefault(
    "DATABASE_URL", "postgresql+asyncpg://landvault:landvault@localhost:5432/landvault_test"
)
os.environ.setdefault("CORS_ALLOWED_ORIGINS", "http://localhost:3000")
os.environ.setdefault("LOG_LEVEL", "INFO")
