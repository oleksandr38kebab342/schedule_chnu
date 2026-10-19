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

    # Опублікований розклад можна дивитися без входу: студент відкриває
    # посилання й одразу бачить пари. Вимикається одним прапорцем, якщо
    # університет вирішить закрити розклад за автентифікацією.
    public_schedule_enabled: bool = True

    # Джерела, яким дозволено звертатися до API з браузера: dev-сервер Vite,
    # його preview і контейнер з Nginx.
    cors_origins: str = "http://localhost:5173,http://localhost:4173,http://localhost:8080"

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


settings = Settings()
