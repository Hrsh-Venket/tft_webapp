"""
Database Connection Management

Provides connection management, pooling, and session handling for both
synchronous and asynchronous database operations.
"""

import time
import logging
from contextlib import contextmanager, asynccontextmanager
from typing import Optional, Dict, Any, Generator, AsyncGenerator
import threading
from functools import wraps

import sqlalchemy as sa
from sqlalchemy import create_engine, text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.pool import QueuePool, StaticPool
from sqlalchemy.exc import SQLAlchemyError, DisconnectionError, TimeoutError
import psycopg2
from psycopg2 import OperationalError as PsycopgOperationalError

from .config import DatabaseConfig, get_database_config

logger = logging.getLogger(__name__)

# SQLAlchemy Base for ORM models
Base = declarative_base()

# Global connection state
_engines: Dict[str, sa.Engine] = {}
_async_engines: Dict[str, sa.ext.asyncio.AsyncEngine] = {}
_session_factories: Dict[str, sessionmaker] = {}
_async_session_factories: Dict[str, sessionmaker] = {}
_lock = threading.RLock()


class DatabaseError(Exception):
    """Base database error."""
    pass


class ConnectionError(DatabaseError):
    """Database connection error."""
    pass


class TimeoutError(DatabaseError):
    """Database timeout error."""
    pass


def retry_on_database_error(max_retries: int = 3, delay: float = 1.0):
    """
    Decorator to retry database operations on connection failures.
    
    Args:
        max_retries: Maximum number of retry attempts
        delay: Delay between retries in seconds
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None
            
            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except (SQLAlchemyError, PsycopgOperationalError, ConnectionError) as e:
                    last_exception = e
                    
                    if attempt < max_retries:
                        logger.warning(f"Database operation failed (attempt {attempt + 1}), retrying in {delay}s: {e}")
                        time.sleep(delay * (2 ** attempt))  # Exponential backoff
                    else:
                        logger.error(f"Database operation failed after {max_retries} retries: {e}")
                        break
                except Exception as e:
                    # Don't retry for non-database errors
                    logger.error(f"Non-database error in database operation: {e}")
                    raise
            
            raise ConnectionError(f"Database operation failed after {max_retries} retries") from last_exception
        
        return wrapper
    return decorator


class DatabaseManager:
    """Centralized database connection manager."""
    
    def __init__(self, config: Optional[DatabaseConfig] = None):
        """Initialize database manager with configuration."""
        self.config = config or get_database_config()
        self._engine: Optional[sa.Engine] = None
        self._async_engine: Optional[sa.ext.asyncio.AsyncEngine] = None
        self._session_factory: Optional[sessionmaker] = None
        self._async_session_factory: Optional[sessionmaker] = None
        self._lock = threading.RLock()
    
    @property
    def engine(self) -> sa.Engine:
        """Get or create synchronous database engine."""
        if self._engine is None:
            with self._lock:
                if self._engine is None:
                    self._engine = self._create_engine()
        return self._engine
    
    @property 
    def async_engine(self) -> sa.ext.asyncio.AsyncEngine:
        """Get or create asynchronous database engine."""
        if self._async_engine is None:
            with self._lock:
                if self._async_engine is None:
                    self._async_engine = self._create_async_engine()
        return self._async_engine
    
    @property
    def session_factory(self) -> sessionmaker:
        """Get or create session factory."""
        if self._session_factory is None:
            with self._lock:
                if self._session_factory is None:
                    self._session_factory = sessionmaker(
                        bind=self.engine,
                        expire_on_commit=False,
                        autoflush=True,
                        autocommit=False
                    )
        return self._session_factory
    
    @property
    def async_session_factory(self) -> sessionmaker:
        """Get or create async session factory."""
        if self._async_session_factory is None:
            with self._lock:
                if self._async_session_factory is None:
                    self._async_session_factory = sessionmaker(
                        self.async_engine,
                        class_=AsyncSession,
                        expire_on_commit=False,
                        autoflush=True,
                        autocommit=False
                    )
        return self._async_session_factory
    
    def _create_engine(self) -> sa.Engine:
        """Create synchronous SQLAlchemy engine."""
        try:
            engine_kwargs = self.config.engine_kwargs
            
            logger.info(f"Creating database engine for {self.config.host}:{self.config.port}")
            logger.debug(f"Engine configuration: {engine_kwargs}")
            
            engine = create_engine(
                self.config.connection_string,
                **engine_kwargs
            )
            
            # Test connection
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
                logger.info("Database engine created and tested successfully")
            
            return engine
            
        except Exception as e:
            logger.error(f"Failed to create database engine: {e}")
            raise ConnectionError(f"Failed to create database engine: {e}") from e
    
    def _create_async_engine(self) -> sa.ext.asyncio.AsyncEngine:
        """Create asynchronous SQLAlchemy engine."""
        try:
            engine_kwargs = self.config.engine_kwargs.copy()
            
            # Remove synchronous-only options
            engine_kwargs.pop('pool_pre_ping', None)
            
            logger.info(f"Creating async database engine for {self.config.host}:{self.config.port}")
            
            engine = create_async_engine(
                self.config.async_connection_string,
                **engine_kwargs
            )
            
            logger.info("Async database engine created successfully")
            return engine
            
        except Exception as e:
            logger.error(f"Failed to create async database engine: {e}")
            raise ConnectionError(f"Failed to create async database engine: {e}") from e
    
    @retry_on_database_error()
    def test_connection(self) -> Dict[str, Any]:
        """
        Test database connection.
        
        Returns:
            Dict with connection test results
        """
        try:
            start_time = time.time()
            
            # Test synchronous connection
            with self.engine.connect() as conn:
                result = conn.execute(text("SELECT version()")).fetchone()
                db_version = result[0] if result else "Unknown"
                
                # Test basic query performance
                conn.execute(text("SELECT 1"))
                
            end_time = time.time()
            response_time = round((end_time - start_time) * 1000, 2)
            
            return {
                "success": True,
                "response_time_ms": response_time,
                "database_version": db_version,
                "connection_info": {
                    "host": self.config.host,
                    "port": self.config.port,
                    "database": self.config.database,
                    "ssl_mode": self.config.ssl_mode,
                    "pool_size": self.config.pool_size if self.config.use_connection_pooling else "disabled"
                }
            }
            
        except Exception as e:
            logger.error(f"Database connection test failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "error_type": type(e).__name__
            }
    
    @contextmanager
    def get_session(self) -> Generator[sa.orm.Session, None, None]:
        """
        Get database session with automatic cleanup.
        
        Usage:
            with db_manager.get_session() as session:
                # Use session
                pass
        """
        session = self.session_factory()
        try:
            yield session
            session.commit()
        except Exception as e:
            session.rollback()
            logger.error(f"Database session error: {e}")
            raise
        finally:
            session.close()
    
    @asynccontextmanager
    async def get_async_session(self) -> AsyncGenerator[AsyncSession, None]:
        """
        Get async database session with automatic cleanup.
        
        Usage:
            async with db_manager.get_async_session() as session:
                # Use async session
                pass
        """
        session = self.async_session_factory()
        try:
            yield session
            await session.commit()
        except Exception as e:
            await session.rollback()
            logger.error(f"Async database session error: {e}")
            raise
        finally:
            await session.close()
    
    def execute_query(self, query: str, params: Optional[Dict[str, Any]] = None) -> Any:
        """
        Execute a raw SQL query.
        
        Args:
            query: SQL query string
            params: Query parameters
            
        Returns:
            Query result
        """
        with self.get_session() as session:
            result = session.execute(text(query), params or {})
            return result.fetchall()
    
    async def execute_async_query(self, query: str, params: Optional[Dict[str, Any]] = None) -> Any:
        """
        Execute a raw SQL query asynchronously.
        
        Args:
            query: SQL query string
            params: Query parameters
            
        Returns:
            Query result
        """
        async with self.get_async_session() as session:
            result = await session.execute(text(query), params or {})
            return result.fetchall()
    
    def get_connection_info(self) -> Dict[str, Any]:
        """Get current connection information."""
        engine = self.engine
        pool = engine.pool
        
        info = {
            "url": str(engine.url).replace(f":{self.config.password}@", ":***@"),
            "pool_size": pool.size() if hasattr(pool, 'size') else "N/A",
            "checked_out": pool.checkedout() if hasattr(pool, 'checkedout') else "N/A",
            "overflow": pool.overflow() if hasattr(pool, 'overflow') else "N/A",
            "checked_in": pool.checkedin() if hasattr(pool, 'checkedin') else "N/A"
        }
        
        return info
    
    def close_connections(self):
        """Close all database connections."""
        try:
            if self._engine:
                self._engine.dispose()
                self._engine = None
                logger.info("Synchronous database engine disposed")
            
            if self._async_engine:
                # Note: async engine disposal should be awaited, but we can't await in sync method
                # This is a known limitation - in production, use proper async disposal
                self._async_engine.sync_dispose()
                self._async_engine = None
                logger.info("Asynchronous database engine disposed")
                
        except Exception as e:
            logger.error(f"Error closing database connections: {e}")


# Global database manager instance
_db_manager: Optional[DatabaseManager] = None


def get_database_manager() -> DatabaseManager:
    """Get or create global database manager instance."""
    global _db_manager
    
    if _db_manager is None:
        with _lock:
            if _db_manager is None:
                _db_manager = DatabaseManager()
    
    return _db_manager


def get_db_engine() -> sa.Engine:
    """Get database engine (global instance)."""
    return get_database_manager().engine


def get_async_db_engine() -> sa.ext.asyncio.AsyncEngine:
    """Get async database engine (global instance)."""
    return get_database_manager().async_engine


@contextmanager
def get_db_session() -> Generator[sa.orm.Session, None, None]:
    """
    Get database session (global instance).
    
    Usage:
        with get_db_session() as session:
            # Use session
            pass
    """
    with get_database_manager().get_session() as session:
        yield session


@asynccontextmanager
async def get_async_db_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Get async database session (global instance).
    
    Usage:
        async with get_async_db_session() as session:
            # Use async session
            pass
    """
    async with get_database_manager().get_async_session() as session:
        yield session


@retry_on_database_error()
def test_connection() -> Dict[str, Any]:
    """Test database connection (global instance)."""
    return get_database_manager().test_connection()


def execute_query(query: str, params: Optional[Dict[str, Any]] = None) -> Any:
    """Execute raw SQL query (global instance)."""
    return get_database_manager().execute_query(query, params)


async def execute_async_query(query: str, params: Optional[Dict[str, Any]] = None) -> Any:
    """Execute raw SQL query asynchronously (global instance)."""
    return await get_database_manager().execute_async_query(query, params)


def get_connection_info() -> Dict[str, Any]:
    """Get connection information (global instance)."""
    return get_database_manager().get_connection_info()


def close_all_connections():
    """Close all database connections (global instance)."""
    global _db_manager
    
    if _db_manager:
        _db_manager.close_connections()
        _db_manager = None


# Health check functions
def health_check() -> Dict[str, Any]:
    """Comprehensive database health check."""
    try:
        db_manager = get_database_manager()
        
        # Test connection
        connection_test = db_manager.test_connection()
        
        # Get connection pool info
        connection_info = db_manager.get_connection_info()
        
        # Test a simple query
        start_time = time.time()
        try:
            result = db_manager.execute_query("SELECT COUNT(*) as table_count FROM information_schema.tables WHERE table_schema = 'public'")
            query_test = {
                "success": True,
                "table_count": result[0][0] if result else 0,
                "response_time_ms": round((time.time() - start_time) * 1000, 2)
            }
        except Exception as e:
            query_test = {
                "success": False,
                "error": str(e)
            }
        
        return {
            "overall_status": "healthy" if connection_test["success"] and query_test["success"] else "unhealthy",
            "connection_test": connection_test,
            "connection_info": connection_info,
            "query_test": query_test,
            "config": db_manager.config.to_dict()
        }
        
    except Exception as e:
        return {
            "overall_status": "unhealthy",
            "error": str(e),
            "error_type": type(e).__name__
        }


# Context manager for temporary database configuration
@contextmanager
def temporary_database_config(config: DatabaseConfig):
    """
    Temporarily use a different database configuration.
    
    Args:
        config: Temporary database configuration
        
    Usage:
        with temporary_database_config(test_config):
            # Use test database
            with get_db_session() as session:
                # This will use test_config
                pass
    """
    global _db_manager
    
    # Save current manager
    original_manager = _db_manager
    
    try:
        # Create temporary manager
        _db_manager = DatabaseManager(config)
        yield _db_manager
    finally:
        # Restore original manager
        if _db_manager and _db_manager != original_manager:
            _db_manager.close_connections()
        _db_manager = original_manager


# Utility function for migrations
def run_migration_script(script_path: str) -> Dict[str, Any]:
    """
    Run a database migration script.
    
    Args:
        script_path: Path to SQL migration script
        
    Returns:
        Migration execution results
    """
    try:
        with open(script_path, 'r') as f:
            migration_sql = f.read()
        
        start_time = time.time()
        
        with get_db_session() as session:
            # Split script into individual statements (basic splitting)
            statements = [stmt.strip() for stmt in migration_sql.split(';') if stmt.strip()]
            
            for statement in statements:
                if statement:
                    session.execute(text(statement))
        
        execution_time = time.time() - start_time
        
        return {
            "success": True,
            "script_path": script_path,
            "statements_executed": len(statements),
            "execution_time_seconds": round(execution_time, 2)
        }
        
    except Exception as e:
        logger.error(f"Migration script failed: {e}")
        return {
            "success": False,
            "script_path": script_path,
            "error": str(e),
            "error_type": type(e).__name__
        }