"""
Production Configuration for TFT Webapp

This module provides production-specific configuration settings for deployment
on Heroku with Supabase database integration.
"""

import os
import logging
from typing import Dict, Any, Optional
from dataclasses import dataclass
import ssl

# Set up logging for configuration module
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@dataclass
class ProductionConfig:
    """Production configuration settings."""
    
    # Application settings
    environment: str = "production"
    debug: bool = False
    app_name: str = "TFT Match Analysis"
    
    # Heroku-specific settings
    port: int = int(os.environ.get("PORT", 8501))
    bind_address: str = "0.0.0.0"
    
    # Database settings
    database_url: Optional[str] = None
    database_ssl_mode: str = "require"
    database_pool_size: int = 10
    database_max_overflow: int = 20
    database_pool_timeout: int = 30
    database_statement_timeout: int = 300000  # 5 minutes
    
    # Supabase settings
    supabase_url: Optional[str] = None
    supabase_anon_key: Optional[str] = None
    supabase_service_key: Optional[str] = None
    
    # Streamlit settings
    streamlit_theme: str = "dark"
    streamlit_primary_color: str = "#FF6B6B"
    
    # Security settings
    secret_key: Optional[str] = None
    allowed_hosts: list = None
    
    # Logging settings
    log_level: str = "INFO"
    log_format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    
    # Performance settings
    enable_caching: bool = True
    cache_ttl: int = 3600  # 1 hour
    
    # External API settings
    tft_api_key: Optional[str] = None
    riot_api_rate_limit: int = 100  # requests per 2 minutes
    
    # Error tracking
    sentry_dsn: Optional[str] = None
    sentry_environment: str = "production"
    
    def __post_init__(self):
        """Load configuration from environment variables."""
        self._load_from_environment()
        self._validate_configuration()
        self._configure_logging()
    
    def _load_from_environment(self):
        """Load configuration values from environment variables."""
        # Application settings
        self.environment = os.environ.get("ENVIRONMENT", self.environment)
        self.debug = os.environ.get("DEBUG", "false").lower() == "true"
        self.app_name = os.environ.get("APP_NAME", self.app_name)
        
        # Heroku settings
        self.port = int(os.environ.get("PORT", self.port))
        
        # Database settings
        self.database_url = os.environ.get("DATABASE_URL")
        self.database_ssl_mode = os.environ.get("DB_SSL_MODE", self.database_ssl_mode)
        self.database_pool_size = int(os.environ.get("DB_POOL_SIZE", self.database_pool_size))
        self.database_max_overflow = int(os.environ.get("DB_MAX_OVERFLOW", self.database_max_overflow))
        self.database_pool_timeout = int(os.environ.get("DB_POOL_TIMEOUT", self.database_pool_timeout))
        self.database_statement_timeout = int(os.environ.get("DB_STATEMENT_TIMEOUT", self.database_statement_timeout))
        
        # Supabase settings
        self.supabase_url = os.environ.get("SUPABASE_URL")
        self.supabase_anon_key = os.environ.get("SUPABASE_ANON_KEY")
        self.supabase_service_key = os.environ.get("SUPABASE_SERVICE_KEY")
        
        # Streamlit settings
        self.streamlit_theme = os.environ.get("STREAMLIT_THEME_BASE", self.streamlit_theme)
        self.streamlit_primary_color = os.environ.get("STREAMLIT_THEME_PRIMARY_COLOR", self.streamlit_primary_color)
        
        # Security settings
        self.secret_key = os.environ.get("SECRET_KEY") or self._generate_secret_key()
        allowed_hosts_str = os.environ.get("ALLOWED_HOSTS", "")
        self.allowed_hosts = [host.strip() for host in allowed_hosts_str.split(",") if host.strip()] or ["*"]
        
        # Logging settings
        self.log_level = os.environ.get("LOG_LEVEL", self.log_level)
        
        # Performance settings
        self.enable_caching = os.environ.get("ENABLE_CACHING", "true").lower() == "true"
        self.cache_ttl = int(os.environ.get("CACHE_TTL", self.cache_ttl))
        
        # External API settings
        self.tft_api_key = os.environ.get("TFT_API_KEY")
        self.riot_api_rate_limit = int(os.environ.get("RIOT_API_RATE_LIMIT", self.riot_api_rate_limit))
        
        # Error tracking
        self.sentry_dsn = os.environ.get("SENTRY_DSN")
        self.sentry_environment = os.environ.get("SENTRY_ENVIRONMENT", self.sentry_environment)
    
    def _generate_secret_key(self) -> str:
        """Generate a secret key if one isn't provided."""
        import secrets
        return secrets.token_urlsafe(32)
    
    def _validate_configuration(self):
        """Validate configuration settings."""
        errors = []
        warnings = []
        
        # Check required settings
        if not self.database_url and not self.supabase_url:
            errors.append("Either DATABASE_URL or SUPABASE_URL must be set")
        
        # Check port
        if not (1 <= self.port <= 65535):
            errors.append(f"Invalid port number: {self.port}")
        
        # Check pool settings
        if self.database_pool_size < 1:
            errors.append("Database pool size must be at least 1")
        
        if self.database_max_overflow < 0:
            errors.append("Database max overflow cannot be negative")
        
        # Warnings for missing optional settings
        if not self.tft_api_key:
            warnings.append("TFT_API_KEY not set - data collection features will be disabled")
        
        if not self.sentry_dsn:
            warnings.append("SENTRY_DSN not set - error tracking will be disabled")
        
        # Log validation results
        if errors:
            logger.error("Configuration validation failed:")
            for error in errors:
                logger.error(f"  - {error}")
            raise ValueError("Invalid configuration")
        
        if warnings:
            logger.warning("Configuration warnings:")
            for warning in warnings:
                logger.warning(f"  - {warning}")
    
    def _configure_logging(self):
        """Configure logging based on settings."""
        # Set log level
        log_level = getattr(logging, self.log_level.upper(), logging.INFO)
        
        # Configure root logger
        logging.basicConfig(
            level=log_level,
            format=self.log_format,
            force=True  # Override existing configuration
        )
        
        # Set specific logger levels
        if not self.debug:
            # Reduce noise from third-party libraries in production
            logging.getLogger("urllib3").setLevel(logging.WARNING)
            logging.getLogger("requests").setLevel(logging.WARNING)
            logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
            logging.getLogger("asyncio").setLevel(logging.WARNING)
    
    def get_database_config(self) -> Dict[str, Any]:
        """Get database configuration dictionary."""
        config = {
            "use_connection_pooling": True,
            "pool_size": self.database_pool_size,
            "max_overflow": self.database_max_overflow,
            "pool_timeout": self.database_pool_timeout,
            "pool_recycle": 3600,  # 1 hour
            "pool_pre_ping": True,
            "ssl_mode": self.database_ssl_mode,
            "application_name": f"{self.app_name}_production",
            "statement_timeout": self.database_statement_timeout,
            "idle_in_transaction_timeout": 60000,  # 1 minute
            "environment": self.environment,
            "debug": self.debug
        }
        
        # Add database URL if available
        if self.database_url:
            config["database_url"] = self.database_url
        
        # Add Supabase-specific settings
        if self.supabase_url:
            config.update({
                "is_supabase": True,
                "supabase_url": self.supabase_url,
                "supabase_key": self.supabase_anon_key,
                "ssl_mode": "require"  # Always require SSL for Supabase
            })
        
        return config
    
    def get_streamlit_config(self) -> Dict[str, Any]:
        """Get Streamlit configuration dictionary."""
        return {
            "server.port": self.port,
            "server.address": self.bind_address,
            "server.headless": True,
            "server.enableCORS": False,
            "server.enableXsrfProtection": False,
            "theme.base": self.streamlit_theme,
            "theme.primaryColor": self.streamlit_primary_color,
            "theme.backgroundColor": "#0E1117" if self.streamlit_theme == "dark" else "#FFFFFF",
            "theme.secondaryBackgroundColor": "#262730" if self.streamlit_theme == "dark" else "#F0F2F6",
            "logger.level": "info" if not self.debug else "debug",
            "client.showErrorDetails": self.debug,
            "client.toolbarMode": "minimal"
        }
    
    def configure_sentry(self):
        """Configure Sentry error tracking if available."""
        if self.sentry_dsn:
            try:
                import sentry_sdk
                from sentry_sdk.integrations.logging import LoggingIntegration
                from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration
                
                sentry_logging = LoggingIntegration(
                    level=logging.INFO,  # Capture info and above as breadcrumbs
                    event_level=logging.ERROR  # Send errors as events
                )
                
                sentry_sdk.init(
                    dsn=self.sentry_dsn,
                    environment=self.sentry_environment,
                    integrations=[
                        sentry_logging,
                        SqlalchemyIntegration()
                    ],
                    traces_sample_rate=0.1,  # 10% of transactions
                    profiles_sample_rate=0.1,  # 10% for profiling
                    attach_stacktrace=True,
                    send_default_pii=False  # Don't send personal info
                )
                
                logger.info("Sentry error tracking configured")
                
            except ImportError:
                logger.warning("Sentry SDK not available - error tracking disabled")
            except Exception as e:
                logger.error(f"Failed to configure Sentry: {e}")
    
    def setup_ssl_context(self) -> Optional[ssl.SSLContext]:
        """Set up SSL context for secure connections."""
        if self.database_ssl_mode == "disable":
            return None
        
        try:
            context = ssl.create_default_context()
            
            # Configure based on SSL mode
            if self.database_ssl_mode == "require":
                context.check_hostname = False
                context.verify_mode = ssl.CERT_REQUIRED
            elif self.database_ssl_mode == "verify-full":
                context.check_hostname = True
                context.verify_mode = ssl.CERT_REQUIRED
            else:
                # For prefer, allow, etc.
                context.check_hostname = False
                context.verify_mode = ssl.CERT_NONE
            
            return context
            
        except Exception as e:
            logger.warning(f"Failed to create SSL context: {e}")
            return None
    
    def is_heroku(self) -> bool:
        """Check if running on Heroku."""
        return "DYNO" in os.environ
    
    def get_heroku_info(self) -> Dict[str, str]:
        """Get Heroku-specific information."""
        return {
            "app_name": os.environ.get("HEROKU_APP_NAME", "unknown"),
            "dyno": os.environ.get("DYNO", "unknown"),
            "release_version": os.environ.get("HEROKU_RELEASE_VERSION", "unknown"),
            "slug_commit": os.environ.get("HEROKU_SLUG_COMMIT", "unknown"),
            "slug_description": os.environ.get("HEROKU_SLUG_DESCRIPTION", "unknown")
        }
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary (excluding sensitive data)."""
        return {
            "environment": self.environment,
            "debug": self.debug,
            "app_name": self.app_name,
            "port": self.port,
            "bind_address": self.bind_address,
            "database_pool_size": self.database_pool_size,
            "database_max_overflow": self.database_max_overflow,
            "database_ssl_mode": self.database_ssl_mode,
            "streamlit_theme": self.streamlit_theme,
            "streamlit_primary_color": self.streamlit_primary_color,
            "log_level": self.log_level,
            "enable_caching": self.enable_caching,
            "cache_ttl": self.cache_ttl,
            "is_heroku": self.is_heroku(),
            "has_database_url": bool(self.database_url),
            "has_supabase_url": bool(self.supabase_url),
            "has_tft_api_key": bool(self.tft_api_key),
            "has_sentry_dsn": bool(self.sentry_dsn)
        }


def get_production_config() -> ProductionConfig:
    """Get production configuration instance."""
    return ProductionConfig()


def configure_streamlit_for_production():
    """Configure Streamlit for production deployment."""
    config = get_production_config()
    streamlit_config = config.get_streamlit_config()
    
    # Set Streamlit configuration
    import streamlit as st
    
    # Configure page
    st.set_page_config(
        page_title=config.app_name,
        page_icon="⚔️",
        layout="wide",
        initial_sidebar_state="collapsed"
    )
    
    # Hide Streamlit menu and footer in production
    if not config.debug:
        hide_streamlit_style = """
        <style>
        #MainMenu {visibility: hidden;}
        footer {visibility: hidden;}
        header {visibility: hidden;}
        .stDeployButton {visibility: hidden;}
        </style>
        """
        st.markdown(hide_streamlit_style, unsafe_allow_html=True)


def setup_production_environment():
    """Set up the complete production environment."""
    config = get_production_config()
    
    # Configure Sentry
    config.configure_sentry()
    
    # Log configuration
    logger.info("Production environment configured")
    logger.info(f"Configuration: {config.to_dict()}")
    
    if config.is_heroku():
        heroku_info = config.get_heroku_info()
        logger.info(f"Heroku deployment info: {heroku_info}")
    
    return config


# Export main configuration function
__all__ = [
    'ProductionConfig',
    'get_production_config',
    'configure_streamlit_for_production',
    'setup_production_environment'
]