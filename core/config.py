from pydantic import SecretStr
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    BOT_TOKEN: SecretStr
    OWNER_ID: int
    ADMIN_ROLE_NAME: str
    HKO_ALERT_CHANNEL_ID: int | None = None
    HKO_ALERT_INTERVAL_MINUTES: int = 5

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
