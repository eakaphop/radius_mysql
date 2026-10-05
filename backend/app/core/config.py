"""Application settings loaded from environment variables (.env)."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Typed settings sourced from environment variables / .env file."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_env: str = "development"
    app_host: str = "0.0.0.0"
    app_port: int = 8001
    app_secret_key: str = "change-me"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7
    cors_origins: str = "http://localhost:5174,http://127.0.0.1:5174"

    db_host: str = "localhost"
    db_port: int = 3306
    db_name: str = "radius"
    db_user: str = "radius_web"
    db_password: str = "change-me"

    radius_password_attribute: str = "Cleartext-Password"
    online_sessions_exclude_usernames: str = ""
    enable_pod: bool = False
    enable_coa: bool = False
    radius_dynauth_port: int = 3799
    radclient_path: str = "/usr/bin/radclient"
    radclient_timeout_sec: int = 5
    freeradius_config_dir: str = "/etc/freeradius/3.0"

    @property
    def cors_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def online_sessions_exclude_usernames_list(self) -> list[str]:
        """RADIUS usernames hidden from Online Sessions — e.g. an admin's own
        office PPPoE account used to reach the web app, not a real customer."""
        return [
            name.strip()
            for name in self.online_sessions_exclude_usernames.split(",")
            if name.strip()
        ]

    @property
    def database_url(self) -> str:
        return (
            f"mysql+asyncmy://{self.db_user}:{self.db_password}"
            f"@{self.db_host}:{self.db_port}/{self.db_name}"
        )


@lru_cache
def get_settings() -> Settings:
    return Settings()
