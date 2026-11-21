"""Application settings and business-rule constants."""
import os
from dataclasses import dataclass
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

# Business rules (all money values are whole rupees).
DELIVERY_FEE = 40
FREE_DELIVERY_ABOVE = 499
TAX_PERCENT = 5
MAX_QTY_PER_ITEM = 10
MAX_DISTINCT_ITEMS = 25


@dataclass(frozen=True)
class Settings:
    database_url: str = f"sqlite:///{BASE_DIR / 'fooddash.db'}"
    secret_key: str = "dev-only-secret-change-me-please-0123456789"
    token_ttl_minutes: int = 60 * 12
    password_iterations: int = 150_000
    seed_on_startup: bool = True
    frontend_dir: Path = BASE_DIR / "frontend"


def get_settings() -> Settings:
    """Build settings from environment variables, falling back to defaults."""
    defaults = Settings()
    return Settings(
        database_url=os.getenv("FOODDASH_DATABASE_URL", defaults.database_url),
        secret_key=os.getenv("FOODDASH_SECRET_KEY", defaults.secret_key),
        token_ttl_minutes=int(os.getenv("FOODDASH_TOKEN_TTL_MINUTES", defaults.token_ttl_minutes)),
    )
