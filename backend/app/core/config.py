from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

# Define the base directory of the application
# This assumes config.py is in app/core/
BASE_DIR = Path(__file__).resolve().parent.parent.parent # This should point to backend/

class Settings(BaseSettings):
    APP_NAME: str = "Regulatory Label AI Checker Backend"
    LOG_LEVEL: str = "INFO" # e.g., DEBUG, INFO, WARNING, ERROR, CRITICAL
    API_V1_STR: str = "/api/v1"

    # File Paths
    # Ensure these are resolved correctly relative to BASE_DIR or are absolute paths
    # These paths will be used by services to know where to save/read files.
    UPLOADS_DIR: Path = BASE_DIR / "uploads"
    STATIC_SERVED_DIR: Path = BASE_DIR / "static_served" # For images with highlights, etc.

    # --- ADDED: Database URL ---
    # This defines the connection string for your database.
    # For SQLite, it's the path to the database file.
    DATABASE_URL: str = f"sqlite:///{BASE_DIR / 'label_checker.db'}"

    # Tesseract OCR Configuration (optional, not currently used with EasyOCR)
    TESSERACT_PATH: str | None = None

    # Security (Example for simple API Key auth - to be used by app/core/security.py)
    # It's best practice to set sensitive values like API_KEY in your .env file
    # API_KEY: str = "your_secret_api_key_here_set_in_env_file"
    # API_KEY_NAME: str = "access_token" # The name of the header or query parameter for the API key

    # Default DPI for image processing if not otherwise specified
    DEFAULT_IMAGE_DPI: int = 300


    # Pydantic model configuration
    model_config = SettingsConfigDict(
        env_file=str(BASE_DIR / ".env"), # Load .env file from backend directory
        env_file_encoding='utf-8',
        extra="ignore" # Ignore extra fields in .env not defined in Settings
    )

# Create an instance of the settings
settings = Settings()

# Ensure critical directories exist when settings are loaded
# This is a good place to do it as settings are imported early.
try:
    settings.UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
    settings.STATIC_SERVED_DIR.mkdir(parents=True, exist_ok=True)
except OSError as e:
    # Handle potential permission errors or other issues during directory creation
    # You might want to log this error or raise a more specific ConfigurationError
    print(f"Warning: Could not create directories {settings.UPLOADS_DIR} or {settings.STATIC_SERVED_DIR}: {e}")

