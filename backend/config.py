import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    SECRET_KEY = os.getenv("SECRET_KEY")
    if not SECRET_KEY:
        raise ValueError("❌ SECRET_KEY env var is required. Set it in .env or deploy config.")
    
    JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY")
    if not JWT_SECRET_KEY:
        raise ValueError("❌ JWT_SECRET_KEY env var is required. Set it in .env or deploy config.")
    
    JWT_ACCESS_TOKEN_EXPIRES = int(os.getenv("JWT_ACCESS_TOKEN_EXPIRES", 3600))
    DB_PATH = os.getenv("DB_PATH", "database/upi_fraud.db")
    DEBUG = os.getenv("DEBUG", "False") == "True"
    FLASK_ENV = os.getenv("FLASK_ENV", "development")
    ML_MODEL_PATH = os.path.join(os.path.dirname(__file__), "..", "ml", "models", "fraud_model.pkl")
    ML_FEATURES_PATH = os.path.join(os.path.dirname(__file__), "..", "ml", "models", "feature_columns.pkl")
    
    # ── CORS & Security config ──────────────────────────────────────
    # Default to localhost for dev; MUST be set to specific domain in production
    ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "http://localhost:5000,http://localhost:3000").split(",")
    ALLOWED_ORIGINS = [origin.strip() for origin in ALLOWED_ORIGINS]  # Clean whitespace
    
    # ── Email alert config ──────────────────────────────────────
    # All email settings are REQUIRED in production; no fallbacks
    ALERT_EMAIL_FROM = os.getenv("ALERT_EMAIL_FROM")
    if not ALERT_EMAIL_FROM and FLASK_ENV == "production":
        raise ValueError("❌ ALERT_EMAIL_FROM env var is required in production.")
    
    ALERT_EMAIL_PASSWORD = os.getenv("ALERT_EMAIL_PASSWORD")
    if not ALERT_EMAIL_PASSWORD and FLASK_ENV == "production":
        raise ValueError("❌ ALERT_EMAIL_PASSWORD env var is required in production.")
    
    ALERT_EMAIL_TO = os.getenv("ALERT_EMAIL_TO")
    if not ALERT_EMAIL_TO and FLASK_ENV == "production":
        raise ValueError("❌ ALERT_EMAIL_TO env var is required in production.")
    
    SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
    SMTP_PORT = int(os.getenv("SMTP_PORT", 587))
