import os
from dataclasses import dataclass

from dotenv import load_dotenv


# Load variables from a .env file in the project root (if present),
# so TAVILY_API_KEY and others are available via os.getenv.
load_dotenv()


@dataclass
class Settings:
    tavily_api_key: str = os.getenv("TAVILY_API_KEY", "")
    mongodb_uri: str = os.getenv("MONGODB_URI", "")
    mongodb_db: str = os.getenv("MONGODB_DB", "obp")
    openai_api_key: str = os.getenv("OPENAI_API_KEY", "")
    openai_model: str = os.getenv("OPENAI_MODEL", "gpt-4.1-mini")

    @property
    def has_tavily_key(self) -> bool:
        return bool(self.tavily_api_key)

    @property
    def has_mongo(self) -> bool:
        return bool(self.mongodb_uri and self.mongodb_db)

    @property
    def has_openai(self) -> bool:
        return bool(self.openai_api_key)


settings = Settings()
