from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Database settings
    DATABASE_URL: str = "postgresql+asyncpg://user:password@localhost:5432/email_db"

    # Server settings
    HOST: str = "0.0.0.0"
    PORT: int = 8080

    # Maildir settings
    MAILDIR_PATH: str = "/root/Maildir/new"
    EMAIL_DOMAIN: str = "example.com"

    # Mail host that custom domains must point their MX record to. A custom
    # domain is considered verified when its MX points here (== mail reaches us).
    MAIL_HOST: str = "mail.example.com"
    MAIL_SERVER_IP: str = "203.0.113.10"

    # Polling interval for new emails (seconds)
    POLL_INTERVAL: int = 10

    # ── Security (see docs/security.md) ──────────────────────────────────────
    # Comma-separated allowed CORS origins, or "*" for any (not recommended in prod).
    CORS_ALLOW_ORIGINS: str = "*"
    # Optional shared admin token. When set, mutating/admin endpoints require the
    # header  X-Admin-Token: <value>. Empty disables (open mode, dev only).
    ADMIN_API_TOKEN: str = ""
    # Requests per minute per client IP (0 = disabled).
    RATE_LIMIT_PER_MINUTE: int = 0
    # Delete stored emails older than this many days (0 = keep forever).
    EMAIL_RETENTION_DAYS: int = 0

    @property
    def cors_origins(self) -> list[str]:
        return [o.strip() for o in self.CORS_ALLOW_ORIGINS.split(",") if o.strip()]

    model_config = SettingsConfigDict(env_file=".env", case_sensitive=True)


settings = Settings()
