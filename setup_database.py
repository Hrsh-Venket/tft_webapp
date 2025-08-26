#!/usr/bin/env python3
"""
TFT Match Analysis Database Setup Script

This script handles database initialization, migration, and setup for both
development and production environments.

Usage:
    python setup_database.py --help
    python setup_database.py init
    python setup_database.py migrate
    python setup_database.py reset
    python setup_database.py test
"""

import os
import sys
import argparse
import logging
from pathlib import Path
from typing import List, Dict, Any
import time

# Add the project root to the path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from database import (
    DatabaseManager, get_database_config, test_connection,
    close_all_connections, health_check
)
from database.connection import run_migration_script
from database.config import validate_config

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('database_setup.log')
    ]
)
logger = logging.getLogger(__name__)


class DatabaseSetup:
    """Database setup and migration manager."""
    
    def __init__(self, config_file: str = ".env"):
        """Initialize database setup."""
        self.config_file = config_file
        self.config = get_database_config(config_file)
        self.db_manager = DatabaseManager(self.config)
        self.migrations_dir = project_root / "database" / "migrations"
        
    def validate_environment(self) -> bool:
        """Validate the current environment and configuration."""
        logger.info("Validating database environment...")
        
        # Validate configuration
        validation = validate_config(self.config)
        if not validation["valid"]:
            logger.error("Configuration validation failed:")
            for issue in validation["issues"]:
                logger.error(f"  - {issue}")
            return False
        
        if validation["warnings"]:
            logger.warning("Configuration warnings:")
            for warning in validation["warnings"]:
                logger.warning(f"  - {warning}")
        
        # Test database connection
        connection_test = test_connection()
        if not connection_test["success"]:
            logger.error(f"Database connection test failed: {connection_test['error']}")
            return False
        
        logger.info(f"Database connection successful (response time: {connection_test['response_time_ms']}ms)")
        logger.info(f"Database version: {connection_test['database_version']}")
        
        return True
    
    def get_migration_files(self) -> List[Path]:
        """Get ordered list of migration files."""
        if not self.migrations_dir.exists():
            logger.error(f"Migrations directory not found: {self.migrations_dir}")
            return []
        
        migration_files = []
        for file_path in sorted(self.migrations_dir.glob("*.sql")):
            if file_path.is_file():
                migration_files.append(file_path)
        
        logger.info(f"Found {len(migration_files)} migration files")
        return migration_files
    
    def check_database_exists(self) -> bool:
        """Check if the database already has tables."""
        try:
            result = self.db_manager.execute_query(
                "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public'"
            )
            table_count = result[0][0] if result else 0
            logger.info(f"Found {table_count} existing tables in database")
            return table_count > 0
            
        except Exception as e:
            logger.error(f"Failed to check database state: {e}")
            return False
    
    def run_migrations(self, force: bool = False) -> bool:
        """Run database migrations."""
        logger.info("Starting database migrations...")
        
        migration_files = self.get_migration_files()
        if not migration_files:
            logger.error("No migration files found")
            return False
        
        # Check if database already exists
        if not force and self.check_database_exists():
            response = input("Database appears to already have tables. Continue with migrations? (y/N): ")
            if response.lower() != 'y':
                logger.info("Migration cancelled by user")
                return False
        
        success_count = 0
        total_time = 0
        
        for migration_file in migration_files:
            logger.info(f"Running migration: {migration_file.name}")
            
            try:
                start_time = time.time()
                result = run_migration_script(str(migration_file))
                
                if result["success"]:
                    execution_time = result["execution_time_seconds"]
                    total_time += execution_time
                    success_count += 1
                    
                    logger.info(
                        f"✓ Migration {migration_file.name} completed successfully "
                        f"({result['statements_executed']} statements, {execution_time:.2f}s)"
                    )
                else:
                    logger.error(
                        f"✗ Migration {migration_file.name} failed: {result['error']}"
                    )
                    return False
                    
            except Exception as e:
                logger.error(f"✗ Migration {migration_file.name} failed with exception: {e}")
                return False
        
        logger.info(
            f"All migrations completed successfully! "
            f"({success_count}/{len(migration_files)} files, {total_time:.2f}s total)"
        )
        return True
    
    def initialize_database(self) -> bool:
        """Initialize a fresh database."""
        logger.info("Initializing fresh database...")
        
        if not self.validate_environment():
            return False
        
        # Run migrations
        if not self.run_migrations():
            return False
        
        # Verify database structure
        if not self.verify_database_structure():
            return False
        
        logger.info("Database initialization completed successfully!")
        return True
    
    def verify_database_structure(self) -> bool:
        """Verify that all expected database objects exist."""
        logger.info("Verifying database structure...")
        
        expected_tables = [
            "matches", "participants", "participant_clusters",
            "participant_units", "participant_traits", "match_statistics", "audit_log"
        ]
        
        expected_views = [
            "player_performance_summary", "meta_analysis", "unit_performance_analysis",
            "match_duration_analysis", "clustering_performance_analysis", "streamlit_dashboard_data"
        ]
        
        expected_functions = [
            "extract_augment_names", "extract_trait_names", "extract_unit_names",
            "calculate_placement_points", "get_player_stats", "validate_match_data"
        ]
        
        try:
            # Check tables
            result = self.db_manager.execute_query(
                "SELECT table_name FROM information_schema.tables WHERE table_schema = 'public' AND table_type = 'BASE TABLE'"
            )
            existing_tables = [row[0] for row in result]
            
            missing_tables = [table for table in expected_tables if table not in existing_tables]
            if missing_tables:
                logger.error(f"Missing tables: {missing_tables}")
                return False
            
            # Check views
            result = self.db_manager.execute_query(
                "SELECT table_name FROM information_schema.views WHERE table_schema = 'public'"
            )
            existing_views = [row[0] for row in result]
            
            missing_views = [view for view in expected_views if view not in existing_views]
            if missing_views:
                logger.warning(f"Missing views: {missing_views}")
            
            # Check functions
            result = self.db_manager.execute_query(
                "SELECT routine_name FROM information_schema.routines WHERE routine_schema = 'public' AND routine_type = 'FUNCTION'"
            )
            existing_functions = [row[0] for row in result]
            
            missing_functions = [func for func in expected_functions if func not in existing_functions]
            if missing_functions:
                logger.warning(f"Missing functions: {missing_functions}")
            
            logger.info(f"✓ Found {len(existing_tables)} tables, {len(existing_views)} views, {len(existing_functions)} functions")
            return True
            
        except Exception as e:
            logger.error(f"Failed to verify database structure: {e}")
            return False
    
    def reset_database(self) -> bool:
        """Reset database by dropping all tables and recreating."""
        logger.warning("⚠️  DATABASE RESET - THIS WILL DELETE ALL DATA!")
        
        if self.config.environment == "production":
            logger.error("Database reset is not allowed in production environment")
            return False
        
        response = input("Are you sure you want to reset the database? This will delete ALL data! (type 'RESET' to confirm): ")
        if response != 'RESET':
            logger.info("Database reset cancelled")
            return False
        
        logger.info("Resetting database...")
        
        try:
            # Drop all tables in reverse order
            drop_queries = [
                "DROP TABLE IF EXISTS audit_log CASCADE",
                "DROP TABLE IF EXISTS match_statistics CASCADE", 
                "DROP TABLE IF EXISTS participant_traits CASCADE",
                "DROP TABLE IF EXISTS participant_units CASCADE",
                "DROP TABLE IF EXISTS participant_clusters CASCADE",
                "DROP TABLE IF EXISTS participants CASCADE",
                "DROP TABLE IF EXISTS matches CASCADE",
                "DROP MATERIALIZED VIEW IF EXISTS mv_current_meta CASCADE",
                "DROP VIEW IF EXISTS streamlit_dashboard_data CASCADE",
                "DROP VIEW IF EXISTS clustering_performance_analysis CASCADE",
                "DROP VIEW IF EXISTS match_duration_analysis CASCADE",
                "DROP VIEW IF EXISTS unit_performance_analysis CASCADE",
                "DROP VIEW IF EXISTS meta_analysis CASCADE",
                "DROP VIEW IF EXISTS player_performance_summary CASCADE",
                "DROP FUNCTION IF EXISTS refresh_materialized_views() CASCADE",
                "DROP FUNCTION IF EXISTS auto_create_partitions() CASCADE",
                "DROP FUNCTION IF EXISTS create_monthly_partition(TEXT, DATE) CASCADE",
                "DROP FUNCTION IF EXISTS update_updated_at_column() CASCADE",
                "DROP FUNCTION IF EXISTS validate_match_data(VARCHAR, INTEGER) CASCADE",
                "DROP FUNCTION IF EXISTS get_match_composition_summary(UUID) CASCADE",
                "DROP FUNCTION IF EXISTS find_similar_compositions(TEXT[], TEXT[], DECIMAL, INTEGER) CASCADE",
                "DROP FUNCTION IF EXISTS get_player_stats(VARCHAR, INTEGER) CASCADE",
                "DROP FUNCTION IF EXISTS match_recency_score(TIMESTAMPTZ) CASCADE",
                "DROP FUNCTION IF EXISTS categorize_placement(INTEGER) CASCADE",
                "DROP FUNCTION IF EXISTS calculate_placement_points(INTEGER) CASCADE",
                "DROP FUNCTION IF EXISTS extract_unit_names(JSONB) CASCADE",
                "DROP FUNCTION IF EXISTS extract_trait_names(JSONB) CASCADE",
                "DROP FUNCTION IF EXISTS extract_augment_names(JSONB) CASCADE",
                "DROP TYPE IF EXISTS participant_placement_type CASCADE",
                "DROP TYPE IF EXISTS game_mode CASCADE",
                "DROP TYPE IF EXISTS match_queue_type CASCADE"
            ]
            
            for query in drop_queries:
                try:
                    self.db_manager.execute_query(query)
                except Exception as e:
                    logger.debug(f"Drop query failed (expected): {query} - {e}")
            
            logger.info("Database reset completed")
            
            # Reinitialize
            return self.initialize_database()
            
        except Exception as e:
            logger.error(f"Database reset failed: {e}")
            return False
    
    def test_database(self) -> bool:
        """Run comprehensive database tests."""
        logger.info("Running database tests...")
        
        try:
            # Test 1: Connection health check
            health = health_check()
            if health["overall_status"] != "healthy":
                logger.error(f"Database health check failed: {health}")
                return False
            
            logger.info("✓ Database health check passed")
            
            # Test 2: Insert test data
            test_match_id = "test_match_" + str(int(time.time()))
            
            insert_query = """
            INSERT INTO matches (game_id, game_datetime, game_length, game_version, queue_id, queue_type, set_core_name, region)
            VALUES (:game_id, NOW(), INTERVAL '25 minutes', '14.1.1', 1100, 'ranked', 'TFTSet14', 'NA1')
            RETURNING match_id
            """
            
            result = self.db_manager.execute_query(insert_query, {"game_id": test_match_id})
            match_id = result[0][0]
            logger.info("✓ Test data insertion passed")
            
            # Test 3: Query test data
            query_result = self.db_manager.execute_query(
                "SELECT game_id FROM matches WHERE match_id = :match_id",
                {"match_id": match_id}
            )
            
            if not query_result or query_result[0][0] != test_match_id:
                logger.error("Test data query failed")
                return False
            
            logger.info("✓ Test data query passed")
            
            # Test 4: Clean up test data
            self.db_manager.execute_query(
                "DELETE FROM matches WHERE match_id = :match_id",
                {"match_id": match_id}
            )
            logger.info("✓ Test data cleanup passed")
            
            # Test 5: Function tests
            function_test = self.db_manager.execute_query(
                "SELECT calculate_placement_points(1) as points"
            )
            
            if function_test[0][0] != 8:
                logger.error("Function test failed")
                return False
            
            logger.info("✓ Function test passed")
            
            logger.info("All database tests passed successfully!")
            return True
            
        except Exception as e:
            logger.error(f"Database test failed: {e}")
            return False
    
    def show_status(self):
        """Show current database status."""
        logger.info("=== Database Status ===")
        
        try:
            config_dict = self.config.to_dict()
            logger.info(f"Environment: {config_dict['environment']}")
            logger.info(f"Host: {config_dict['host']}:{config_dict['port']}")
            logger.info(f"Database: {config_dict['database']}")
            logger.info(f"Username: {config_dict['username']}")
            logger.info(f"SSL Mode: {config_dict['ssl_mode']}")
            logger.info(f"Connection Pooling: {config_dict['use_connection_pooling']}")
            
            if config_dict['use_connection_pooling']:
                logger.info(f"Pool Size: {config_dict['pool_size']}")
                logger.info(f"Max Overflow: {config_dict['max_overflow']}")
            
            # Connection info
            conn_info = self.db_manager.get_connection_info()
            logger.info(f"Connection URL: {conn_info['url']}")
            
            if conn_info['pool_size'] != "N/A":
                logger.info(f"Pool Status - Size: {conn_info['pool_size']}, Checked Out: {conn_info['checked_out']}")
            
            # Table counts
            result = self.db_manager.execute_query(
                """SELECT 
                    schemaname, 
                    COUNT(*) as table_count
                   FROM pg_tables 
                   WHERE schemaname = 'public'
                   GROUP BY schemaname"""
            )
            
            if result:
                logger.info(f"Tables in public schema: {result[0][1]}")
            
            # Recent activity
            try:
                result = self.db_manager.execute_query(
                    "SELECT COUNT(*) FROM matches WHERE game_datetime >= NOW() - INTERVAL '24 hours'"
                )
                recent_matches = result[0][0] if result else 0
                logger.info(f"Matches in last 24 hours: {recent_matches}")
                
            except Exception:
                logger.info("No match data available")
                
        except Exception as e:
            logger.error(f"Failed to get database status: {e}")
    
    def cleanup(self):
        """Cleanup database connections."""
        try:
            self.db_manager.close_connections()
            close_all_connections()
            logger.info("Database connections closed")
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")


def main():
    """Main entry point for the database setup script."""
    parser = argparse.ArgumentParser(
        description="TFT Match Analysis Database Setup",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument(
        "command",
        choices=["init", "migrate", "reset", "test", "status"],
        help="Command to execute"
    )
    
    parser.add_argument(
        "--config",
        default=".env",
        help="Configuration file path (default: .env)"
    )
    
    parser.add_argument(
        "--force",
        action="store_true",
        help="Force operation without confirmation"
    )
    
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose logging"
    )
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Initialize database setup
    try:
        db_setup = DatabaseSetup(args.config)
        
        if args.command == "init":
            success = db_setup.initialize_database()
            
        elif args.command == "migrate":
            success = db_setup.run_migrations(force=args.force)
            
        elif args.command == "reset":
            success = db_setup.reset_database()
            
        elif args.command == "test":
            success = db_setup.test_database()
            
        elif args.command == "status":
            db_setup.show_status()
            success = True
            
        else:
            logger.error(f"Unknown command: {args.command}")
            success = False
        
        # Cleanup
        db_setup.cleanup()
        
        # Exit with appropriate code
        sys.exit(0 if success else 1)
        
    except KeyboardInterrupt:
        logger.info("Operation cancelled by user")
        sys.exit(1)
        
    except Exception as e:
        logger.error(f"Setup script failed: {e}")
        if args.verbose:
            raise
        sys.exit(1)


if __name__ == "__main__":
    main()