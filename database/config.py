"""
Database Configuration Management

Handles database configuration for different environments (development, production)
with support for both local PostgreSQL and Supabase deployments.
"""

import os
import logging
from dataclasses import dataclass
from typing import Optional, Dict, Any
from urllib.parse import urlparse
import json

# Streamlit Cloud secrets support
try:
    import streamlit as st
    STREAMLIT_AVAILABLE = True
except ImportError:
    STREAMLIT_AVAILABLE = False

logger = logging.getLogger(__name__)

@dataclass
class DatabaseConfig:
    """Database configuration container."""
    
    # Connection parameters
    host: str
    port: int
    database: str
    username: str
    password: str
    
    # Connection string (optional, overrides individual parameters)
    database_url: Optional[str] = None
    
    # Connection pooling settings
    use_connection_pooling: bool = True
    pool_size: int = 20
    max_overflow: int = 30
    pool_timeout: int = 30
    pool_recycle: int = 3600
    pool_pre_ping: bool = True
    
    # SSL settings
    ssl_mode: str = "prefer"  # disable, allow, prefer, require, verify-ca, verify-full
    ssl_cert: Optional[str] = None
    ssl_key: Optional[str] = None
    ssl_ca: Optional[str] = None
    
    # Application settings
    application_name: str = "tft_match_analysis"
    schema: str = "public"
    
    # Supabase specific settings
    is_supabase: bool = False
    supabase_url: Optional[str] = None
    supabase_key: Optional[str] = None
    
    # Connection retry settings
    max_retries: int = 3
    retry_delay: float = 1.0
    
    # Query settings
    statement_timeout: int = 300000  # 5 minutes in milliseconds
    idle_in_transaction_timeout: int = 60000  # 1 minute in milliseconds
    
    # Environment
    environment: str = "development"
    debug: bool = False

    def __post_init__(self):
        """Validate configuration after initialization."""
        if self.database_url:
            self._parse_database_url()
        
        # Validate required fields
        if not all([self.host, self.port, self.database, self.username]):
            raise ValueError("Missing required database configuration parameters")
        
        # Auto-detect Supabase
        if "supabase.co" in self.host or "supabase" in self.host.lower():
            self.is_supabase = True
            if not self.supabase_url:
                self.supabase_url = f"https://{self.host.split('.')[0]}.supabase.co"
        
        # Set SSL defaults for Supabase
        if self.is_supabase and self.ssl_mode == "prefer":
            self.ssl_mode = "require"

    def _parse_database_url(self):
        """Parse DATABASE_URL into component parts."""
        try:
            parsed = urlparse(self.database_url)
            
            self.username = parsed.username or self.username
            self.password = parsed.password or self.password
            self.host = parsed.hostname or self.host
            self.port = parsed.port or self.port
            self.database = parsed.path.lstrip('/') or self.database
            
            # Parse query parameters for additional settings
            if parsed.query:
                params = dict(param.split('=') for param in parsed.query.split('&') if '=' in param)
                if 'sslmode' in params:
                    self.ssl_mode = params['sslmode']
                    
        except Exception as e:
            logger.warning(f"Failed to parse database URL: {e}")

    @property
    def connection_string(self) -> str:
        """Generate SQLAlchemy connection string."""
        if self.database_url:
            return self.database_url
        
        # Build connection string
        conn_str = f"postgresql://{self.username}:{self.password}@{self.host}:{self.port}/{self.database}"
        
        # Add query parameters
        params = []
        
        if self.ssl_mode != "prefer":
            params.append(f"sslmode={self.ssl_mode}")
        
        if self.application_name:
            params.append(f"application_name={self.application_name}")
        
        if params:
            conn_str += "?" + "&".join(params)
        
        return conn_str

    @property
    def async_connection_string(self) -> str:
        """Generate async SQLAlchemy connection string."""
        return self.connection_string.replace("postgresql://", "postgresql+asyncpg://")

    @property
    def engine_kwargs(self) -> Dict[str, Any]:
        """Get SQLAlchemy engine configuration."""
        kwargs = {
            "echo": self.debug,
            "pool_pre_ping": self.pool_pre_ping,
            "connect_args": {
                "application_name": self.application_name,
                "options": f"-c default_transaction_isolation=read_committed -c statement_timeout={self.statement_timeout} -c idle_in_transaction_session_timeout={self.idle_in_transaction_timeout}"
            }
        }
        
        # Add pooling configuration if enabled
        if self.use_connection_pooling:
            kwargs.update({
                "pool_size": self.pool_size,
                "max_overflow": self.max_overflow,
                "pool_timeout": self.pool_timeout,
                "pool_recycle": self.pool_recycle,
            })
        else:
            kwargs["poolclass"] = "StaticPool"
        
        # Add SSL configuration if needed
        if self.ssl_cert or self.ssl_key or self.ssl_ca:
            ssl_args = {}
            if self.ssl_cert:
                ssl_args["sslcert"] = self.ssl_cert
            if self.ssl_key:
                ssl_args["sslkey"] = self.ssl_key
            if self.ssl_ca:
                ssl_args["sslrootcert"] = self.ssl_ca
            kwargs["connect_args"].update(ssl_args)
        
        return kwargs

    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary (excluding sensitive data)."""
        return {
            "host": self.host,
            "port": self.port,
            "database": self.database,
            "username": self.username,
            "password": "***" if self.password else None,
            "use_connection_pooling": self.use_connection_pooling,
            "pool_size": self.pool_size,
            "max_overflow": self.max_overflow,
            "ssl_mode": self.ssl_mode,
            "application_name": self.application_name,
            "schema": self.schema,
            "is_supabase": self.is_supabase,
            "environment": self.environment,
            "debug": self.debug
        }


def load_env_file(env_file_path: str = ".env") -> Dict[str, str]:
    """Load environment variables from .env file."""
    env_vars = {}
    
    try:
        if os.path.exists(env_file_path):
            with open(env_file_path, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        key, value = line.split('=', 1)
                        env_vars[key.strip()] = value.strip().strip('"\'')
        
        # Override with actual environment variables
        env_vars.update(os.environ)
        
    except Exception as e:
        logger.warning(f"Failed to load .env file: {e}")
    
    return env_vars


def get_database_config(env_file: str = ".env") -> DatabaseConfig:
    """
    Load database configuration from environment variables.
    
    Environment variables (in order of precedence):
    1. Streamlit Cloud secrets (if available)
    2. DATABASE_URL (full connection string)
    3. Individual components:
       - DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD
       - SUPABASE_DB_HOST, SUPABASE_DB_PASSWORD (for Supabase)
    4. Default values for development
    
    Args:
        env_file: Path to .env file
        
    Returns:
        DatabaseConfig: Configured database settings
    """
    env_vars = load_env_file(env_file)
    
    # Try to get database URL from Streamlit secrets first
    if STREAMLIT_AVAILABLE:
        try:
            database_url = st.secrets.get("database", {}).get("DATABASE_URL")
            if database_url:
                env_vars["DATABASE_URL"] = database_url
        except Exception:
            pass
    
    # Check if we're in production (Heroku sets this)
    is_prod = env_vars.get("ENVIRONMENT", "").lower() == "production" or \
              env_vars.get("HEROKU", "").lower() == "true" or \
              "DYNO" in env_vars
    
    # Get database URL (Heroku style)
    database_url = env_vars.get("DATABASE_URL")
    
    # Configuration defaults
    config_data = {
        "environment": "production" if is_prod else "development",
        "debug": env_vars.get("DEBUG", "false").lower() == "true" and not is_prod,
        "database_url": database_url
    }
    
    # Supabase configuration
    if env_vars.get("SUPABASE_DB_HOST"):
        config_data.update({
            "host": env_vars["SUPABASE_DB_HOST"],
            "port": int(env_vars.get("SUPABASE_DB_PORT", 5432)),
            "database": env_vars.get("SUPABASE_DB_NAME", "postgres"),
            "username": env_vars.get("SUPABASE_DB_USER", "postgres"),
            "password": env_vars["SUPABASE_DB_PASSWORD"],
            "is_supabase": True,
            "supabase_url": env_vars.get("SUPABASE_URL"),
            "supabase_key": env_vars.get("SUPABASE_ANON_KEY"),
            "ssl_mode": "require"
        })
    
    # Regular PostgreSQL configuration
    else:
        config_data.update({
            "host": env_vars.get("DB_HOST", "localhost"),
            "port": int(env_vars.get("DB_PORT", 6432 if is_prod else 6432)),  # PgBouncer port
            "database": env_vars.get("DB_NAME", "tft_matches"),
            "username": env_vars.get("DB_USER", "tft_user"),
            "password": env_vars.get("DB_PASSWORD", "tft_password")
        })
    
    # Connection pooling settings
    config_data.update({
        "use_connection_pooling": env_vars.get("DB_USE_POOLING", "true").lower() == "true",
        "pool_size": int(env_vars.get("DB_POOL_SIZE", 20)),
        "max_overflow": int(env_vars.get("DB_MAX_OVERFLOW", 30)),
        "pool_timeout": int(env_vars.get("DB_POOL_TIMEOUT", 30)),
        "pool_recycle": int(env_vars.get("DB_POOL_RECYCLE", 3600))
    })
    
    # SSL settings
    config_data.update({
        "ssl_mode": env_vars.get("DB_SSL_MODE", "require" if is_prod else "prefer"),
        "ssl_cert": env_vars.get("DB_SSL_CERT"),
        "ssl_key": env_vars.get("DB_SSL_KEY"),
        "ssl_ca": env_vars.get("DB_SSL_CA")
    })
    
    # Performance settings
    config_data.update({
        "max_retries": int(env_vars.get("DB_MAX_RETRIES", 3)),
        "retry_delay": float(env_vars.get("DB_RETRY_DELAY", 1.0)),
        "statement_timeout": int(env_vars.get("DB_STATEMENT_TIMEOUT", 300000)),
        "idle_in_transaction_timeout": int(env_vars.get("DB_IDLE_TIMEOUT", 60000))
    })
    
    return DatabaseConfig(**config_data)


def is_production() -> bool:
    """Check if we're running in production environment."""
    return os.environ.get("ENVIRONMENT", "").lower() == "production" or \
           os.environ.get("HEROKU", "").lower() == "true" or \
           "DYNO" in os.environ


def is_development() -> bool:
    """Check if we're running in development environment."""
    return not is_production()


def get_heroku_config() -> Optional[DatabaseConfig]:
    """Get Heroku-specific database configuration."""
    database_url = os.environ.get("DATABASE_URL")
    
    if not database_url:
        return None
    
    return DatabaseConfig(
        host="",  # Will be parsed from database_url
        port=5432,  # Will be parsed from database_url
        database="",  # Will be parsed from database_url
        username="",  # Will be parsed from database_url
        password="",  # Will be parsed from database_url
        database_url=database_url,
        environment="production",
        ssl_mode="require",
        use_connection_pooling=True,
        pool_size=int(os.environ.get("DB_POOL_SIZE", 10)),  # Smaller for Heroku
        max_overflow=int(os.environ.get("DB_MAX_OVERFLOW", 20))
    )


def validate_config(config: DatabaseConfig) -> Dict[str, Any]:
    """
    Validate database configuration.
    
    Args:
        config: Database configuration to validate
        
    Returns:
        Dict with validation results
    """
    issues = []
    warnings = []
    
    # Required fields validation
    if not config.host:
        issues.append("Database host is required")
    
    if not config.database:
        issues.append("Database name is required")
    
    if not config.username:
        issues.append("Database username is required")
    
    if not config.password:
        issues.append("Database password is required")
    
    # Port validation
    if not (1 <= config.port <= 65535):
        issues.append(f"Invalid port number: {config.port}")
    
    # Pool size validation
    if config.use_connection_pooling:
        if config.pool_size < 1:
            issues.append("Pool size must be at least 1")
        
        if config.pool_size > 100:
            warnings.append("Pool size is quite large (>100)")
        
        if config.max_overflow < 0:
            issues.append("Max overflow cannot be negative")
    
    # SSL validation
    valid_ssl_modes = ["disable", "allow", "prefer", "require", "verify-ca", "verify-full"]
    if config.ssl_mode not in valid_ssl_modes:
        issues.append(f"Invalid SSL mode: {config.ssl_mode}")
    
    # Supabase validation
    if config.is_supabase and config.ssl_mode == "disable":
        warnings.append("SSL is disabled for Supabase connection")
    
    return {
        "valid": len(issues) == 0,
        "issues": issues,
        "warnings": warnings
    }