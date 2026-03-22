import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key")
    JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "jwt-dev-key")
    JWT_ACCESS_TOKEN_EXPIRES = int(os.getenv("JWT_ACCESS_TOKEN_EXPIRES", 3600))
    DB_PATH = os.getenv("DB_PATH", "database/upi_fraud.db")
    DEBUG = os.getenv("DEBUG", "True") == "True"
    FLASK_ENV = os.getenv("FLASK_ENV", "development")
    ML_MODEL_PATH = os.path.join(os.path.dirname(__file__), "..", "ml", "models", "fraud_model.pkl")
    ML_FEATURES_PATH = os.path.join(os.path.dirname(__file__), "..", "ml", "models", "feature_columns.pkl")
    # ── Email alert config ──────────────────────────────────────
    ALERT_EMAIL_FROM     = os.getenv("ALERT_EMAIL_FROM", "junnupravalika59@gmail.com")
    ALERT_EMAIL_PASSWORD = os.getenv("ALERT_EMAIL_PASSWORD", "eztxtvpnztfisvco")
    ALERT_EMAIL_TO       = os.getenv("ALERT_EMAIL_TO", "junnupravalika59@gmail.com")
    SMTP_HOST            = os.getenv("SMTP_HOST", "smtp.gmail.com")
    SMTP_PORT            = int(os.getenv("SMTP_PORT", 587))
