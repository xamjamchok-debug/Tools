import os
from dotenv import load_dotenv

load_dotenv()


class _Config:
    def __init__(self):
        self.azure_connection_string = self._require("AZURE_STORAGE_CONNECTION_STRING")
        self.anthropic_api_key = self._require("ANTHROPIC_API_KEY")

    def _require(self, key: str) -> str:
        value = os.getenv(key)
        if not value:
            raise EnvironmentError(
                f"Required env var '{key}' not set — check your .env file."
            )
        return value


config = _Config()
