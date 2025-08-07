"""
TFT Match Analysis Database Package

This package provides database connectivity, migration management, and data access
utilities for the TFT (Teamfight Tactics) match analysis application.

Key Components:
- connection.py: Database connection management with pooling
- config.py: Configuration management for different environments
- Migration system: SQL-based database migrations
- Helper functions: Utilities for database operations

Usage:
    from database import get_db_engine, get_db_session
    from database.connection import DatabaseManager
    
    # Get database engine
    engine = get_db_engine()
    
    # Get database session
    with get_db_session() as session:
        # Perform database operations
        pass
"""

from .connection import (
    DatabaseManager,
    get_db_engine,
    get_db_session,
    get_async_db_engine,
    get_async_db_session,
    test_connection,
    close_all_connections
)

from .config import (
    DatabaseConfig,
    get_database_config,
    is_production,
    is_development
)

# Version information
__version__ = "1.0.0"
__author__ = "TFT Analytics Team"

# Package-level exports
__all__ = [
    # Connection management
    "DatabaseManager",
    "get_db_engine", 
    "get_db_session",
    "get_async_db_engine",
    "get_async_db_session",
    "test_connection",
    "close_all_connections",
    
    # Configuration
    "DatabaseConfig",
    "get_database_config",
    "is_production",
    "is_development",
    
    # Version
    "__version__"
]

# Initialize package-level logger
import logging

logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())  # Prevent "No handler found" warnings

# Package initialization
def initialize_database():
    """Initialize the database package and test connections."""
    try:
        from .connection import DatabaseManager
        
        # Test database connection
        db_manager = DatabaseManager()
        if db_manager.test_connection():
            logger.info("Database package initialized successfully")
            return True
        else:
            logger.error("Database connection test failed")
            return False
            
    except Exception as e:
        logger.error(f"Failed to initialize database package: {e}")
        return False

# Health check function
def health_check():
    """
    Perform a health check on the database system.
    
    Returns:
        dict: Health check results with status and details
    """
    try:
        from .connection import test_connection
        from .config import get_database_config
        
        config = get_database_config()
        
        health_status = {
            "status": "healthy",
            "database_type": "supabase" if config.is_supabase else "postgresql",
            "connection_pooling": config.use_connection_pooling,
            "environment": "production" if is_production() else "development",
            "details": {}
        }
        
        # Test database connection
        connection_test = test_connection()
        if connection_test["success"]:
            health_status["details"]["connection"] = "OK"
        else:
            health_status["status"] = "unhealthy"
            health_status["details"]["connection"] = f"FAILED: {connection_test['error']}"
        
        return health_status
        
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e),
            "details": {}
        }

# Cleanup function for graceful shutdown
def cleanup():
    """Clean up database connections and resources."""
    try:
        close_all_connections()
        logger.info("Database package cleanup completed")
    except Exception as e:
        logger.error(f"Error during database cleanup: {e}")