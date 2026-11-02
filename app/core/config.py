from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    APP_NAME: str = "HemoTrack"
    APP_ENV: str = "development"
    DEBUG: bool = True

    DATABASE_URL: str = "mysql+pymysql://hemotrack:hemotrack@localhost:3306/hemotrack"

    SECRET_KEY: str = "change-me-to-a-long-random-secret-key"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 480
    ALGORITHM: str = "HS256"

    ADMIN_EMAIL: str = "admin@hemotrack.com"
    ADMIN_PASSWORD: str = "Admin@123"
    ADMIN_FULL_NAME: str = "System Admin"

    CORS_ORIGINS: list[str] = [
        "http://localhost:3000",
        "http://localhost:5173",
        "https://hemotrackbtms.netlify.app",
    ]


settings = Settings()
