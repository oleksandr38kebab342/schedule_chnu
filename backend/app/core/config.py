from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+psycopg://rozklad:rozklad@localhost:5432/rozklad"
    redis_url: str = "redis://localhost:6379/0"

    # HS256 вимагає ключ від 32 байтів (RFC 7518); у production замінити на openssl rand -hex 32.
    jwt_secret: str = "dev-only-secret-replace-me-before-deploy"
    jwt_algorithm: str = "HS256"
    access_token_ttl_minutes: int = 480

    seed_admin_email: str = "admin@chnu.edu.ua"
    seed_admin_password: str = "admin12345"


settings = Settings()
