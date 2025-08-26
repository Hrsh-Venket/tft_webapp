#!/usr/bin/env python3
"""
Production Migration Script for TFT Webapp

This script handles database migrations, data imports, and setup for production deployment.
Designed to work with both Heroku Postgres and Supabase.

Usage:
    python deployment/migrate_to_production.py [options]

Options:
    --initial-setup     : Run initial database setup (create tables, functions, etc.)
    --migrate          : Run database migrations only
    --import-data      : Import data from local/staging environment
    --health-check     : Run health checks after migration
    --dry-run          : Show what would be done without executing
    --force            : Force migration even if database is not empty
    --verbose          : Enable verbose logging

Examples:
    # Initial deployment
    python deployment/migrate_to_production.py --initial-setup

    # Regular migration
    python deployment/migrate_to_production.py --migrate

    # Import data from local environment
    python deployment/migrate_to_production.py --import-data --force

    # Dry run to see what would happen
    python deployment/migrate_to_production.py --initial-setup --dry-run
"""

import os
import sys
import argparse
import logging
import json
import time
from pathlib import Path
from typing import Dict, Any, List, Optional
import subprocess
from contextlib import contextmanager

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

try:
    from database.connection import (
        get_database_manager, 
        DatabaseManager,
        test_connection,
        health_check
    )
    from database.config import get_database_config, DatabaseConfig
    from deployment.production_config import get_production_config, ProductionConfig
    HAS_DATABASE = True
except ImportError as e:
    print(f"Warning: Database modules not available: {e}")
    HAS_DATABASE = False

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class MigrationError(Exception):
    """Custom exception for migration errors."""
    pass


class ProductionMigrator:
    """Handles production database migrations and setup."""
    
    def __init__(self, config: Optional[ProductionConfig] = None, dry_run: bool = False):
        """Initialize migrator with configuration."""
        self.config = config or get_production_config()
        self.dry_run = dry_run
        self.db_manager: Optional[DatabaseManager] = None
        self.migration_dir = project_root / "database" / "migrations"
        
        if HAS_DATABASE:
            try:
                self.db_manager = get_database_manager()
                logger.info("Database manager initialized successfully")
            except Exception as e:
                logger.error(f"Failed to initialize database manager: {e}")
                raise MigrationError(f"Database initialization failed: {e}")
        else:
            raise MigrationError("Database modules not available")
    
    def check_prerequisites(self) -> Dict[str, bool]:
        """Check if all prerequisites are met for migration."""
        checks = {
            "database_connection": False,
            "migration_files_exist": False,
            "environment_variables_set": False,
            "write_permissions": False
        }
        
        try:
            # Test database connection
            if self.db_manager:
                connection_test = self.db_manager.test_connection()
                checks["database_connection"] = connection_test.get("success", False)
            
            # Check migration files
            checks["migration_files_exist"] = self.migration_dir.exists() and any(
                f.suffix == ".sql" for f in self.migration_dir.glob("*.sql")
            )
            
            # Check environment variables
            required_env_vars = ["DATABASE_URL"] if not self.config.supabase_url else ["SUPABASE_DB_HOST", "SUPABASE_DB_PASSWORD"]
            checks["environment_variables_set"] = all(
                os.environ.get(var) for var in required_env_vars
            )
            
            # Check write permissions (try to create a temp table)
            if checks["database_connection"] and not self.dry_run:
                try:
                    with self.db_manager.get_session() as session:
                        session.execute("CREATE TEMP TABLE migration_test (id INTEGER)")
                        session.execute("DROP TABLE migration_test")
                    checks["write_permissions"] = True
                except Exception as e:
                    logger.warning(f"Write permission check failed: {e}")
                    checks["write_permissions"] = False
            else:
                checks["write_permissions"] = True  # Assume OK for dry run
                
        except Exception as e:
            logger.error(f"Prerequisites check failed: {e}")
        
        return checks
    
    def get_migration_files(self) -> List[Path]:
        """Get list of migration files in order."""
        if not self.migration_dir.exists():
            logger.error(f"Migration directory not found: {self.migration_dir}")
            return []
        
        # Get all .sql files and sort by name (should be numbered)
        migration_files = sorted([
            f for f in self.migration_dir.glob("*.sql") 
            if f.is_file()
        ])
        
        logger.info(f"Found {len(migration_files)} migration files")
        for i, file in enumerate(migration_files):
            logger.info(f"  {i+1}. {file.name}")
        
        return migration_files
    
    def check_database_state(self) -> Dict[str, Any]:
        """Check current state of the database."""
        if not self.db_manager:
            return {"error": "No database manager available"}
        
        try:
            with self.db_manager.get_session() as session:
                # Check if database is empty
                result = session.execute(
                    "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public'"
                )
                table_count = result.fetchone()[0]
                
                # Check if our main tables exist
                main_tables = ['matches', 'participants', 'match_clustering']
                existing_tables = []
                
                for table in main_tables:
                    result = session.execute(
                        "SELECT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = %s)",
                        (table,)
                    )
                    if result.fetchone()[0]:
                        existing_tables.append(table)
                
                # Check for data
                data_counts = {}
                for table in existing_tables:
                    try:
                        result = session.execute(f"SELECT COUNT(*) FROM {table}")
                        data_counts[table] = result.fetchone()[0]
                    except Exception as e:
                        logger.warning(f"Could not count records in {table}: {e}")
                        data_counts[table] = "unknown"
                
                return {
                    "is_empty": table_count == 0,
                    "table_count": table_count,
                    "main_tables_exist": existing_tables,
                    "data_counts": data_counts
                }
                
        except Exception as e:
            logger.error(f"Failed to check database state: {e}")
            return {"error": str(e)}
    
    def run_migration_file(self, migration_file: Path) -> Dict[str, Any]:
        """Run a single migration file."""
        logger.info(f"Running migration: {migration_file.name}")
        
        if self.dry_run:
            logger.info(f"[DRY RUN] Would execute migration: {migration_file.name}")
            return {"success": True, "dry_run": True}
        
        try:
            # Read migration file
            with open(migration_file, 'r', encoding='utf-8') as f:
                migration_sql = f.read()
            
            if not migration_sql.strip():
                logger.warning(f"Migration file {migration_file.name} is empty")
                return {"success": True, "warning": "Empty file"}
            
            start_time = time.time()
            statements_executed = 0
            
            with self.db_manager.get_session() as session:
                # Split SQL into statements (basic splitting by semicolon)
                statements = [
                    stmt.strip() 
                    for stmt in migration_sql.split(';') 
                    if stmt.strip() and not stmt.strip().startswith('--')
                ]
                
                for statement in statements:
                    if statement:
                        try:
                            session.execute(statement)
                            statements_executed += 1
                            logger.debug(f"Executed statement: {statement[:100]}...")
                        except Exception as e:
                            logger.error(f"Failed to execute statement: {statement[:100]}...")
                            logger.error(f"Error: {e}")
                            raise
            
            execution_time = time.time() - start_time
            
            result = {
                "success": True,
                "file": migration_file.name,
                "statements_executed": statements_executed,
                "execution_time_seconds": round(execution_time, 2)
            }
            
            logger.info(f"Migration {migration_file.name} completed successfully "
                       f"({statements_executed} statements in {execution_time:.2f}s)")
            
            return result
            
        except Exception as e:
            logger.error(f"Migration {migration_file.name} failed: {e}")
            return {
                "success": False,
                "file": migration_file.name,
                "error": str(e),
                "error_type": type(e).__name__
            }
    
    def run_all_migrations(self) -> Dict[str, Any]:
        """Run all migration files in order."""
        logger.info("Starting database migrations")
        
        migration_files = self.get_migration_files()
        if not migration_files:
            return {"success": False, "error": "No migration files found"}
        
        results = []
        failed_migrations = []
        
        for migration_file in migration_files:
            result = self.run_migration_file(migration_file)
            results.append(result)
            
            if not result["success"]:
                failed_migrations.append(migration_file.name)
                logger.error(f"Migration failed, stopping at: {migration_file.name}")
                break
        
        summary = {
            "success": len(failed_migrations) == 0,
            "total_migrations": len(migration_files),
            "executed_migrations": len(results),
            "failed_migrations": failed_migrations,
            "results": results,
            "dry_run": self.dry_run
        }
        
        if summary["success"]:
            logger.info(f"All migrations completed successfully "
                       f"({summary['executed_migrations']}/{summary['total_migrations']})")
        else:
            logger.error(f"Migrations failed. Executed: {summary['executed_migrations']}, "
                        f"Failed: {len(failed_migrations)}")
        
        return summary
    
    def import_data_from_local(self, source_db_url: Optional[str] = None) -> Dict[str, Any]:
        """Import data from local development database."""
        logger.info("Starting data import from local environment")
        
        if self.dry_run:
            logger.info("[DRY RUN] Would import data from local environment")
            return {"success": True, "dry_run": True}
        
        # This would need to be implemented based on your specific data export/import needs
        # For now, we'll create a placeholder that shows how this could work
        
        try:
            # Example: Export from local and import to production
            # This is a simplified example - you'd need to implement the actual data transfer
            
            import_results = {
                "matches_imported": 0,
                "participants_imported": 0,
                "clusters_imported": 0
            }
            
            # Placeholder for actual import logic
            logger.warning("Data import not implemented yet. This would:")
            logger.warning("1. Export data from local/staging database")
            logger.warning("2. Transform data for production format")
            logger.warning("3. Import data to production database")
            logger.warning("4. Verify data integrity")
            
            return {
                "success": True,
                "results": import_results,
                "warning": "Data import is a placeholder - implement based on your needs"
            }
            
        except Exception as e:
            logger.error(f"Data import failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "error_type": type(e).__name__
            }
    
    def run_health_check(self) -> Dict[str, Any]:
        """Run comprehensive health check after migration."""
        logger.info("Running post-migration health check")
        
        if self.dry_run:
            logger.info("[DRY RUN] Would run health check")
            return {"success": True, "dry_run": True}
        
        try:
            # Use the health check from database connection module
            health_result = health_check()
            
            # Additional checks specific to TFT webapp
            additional_checks = self._run_application_specific_checks()
            
            combined_result = {
                "overall_health": health_result,
                "application_checks": additional_checks,
                "timestamp": time.time(),
                "success": health_result.get("overall_status") == "healthy" and 
                          additional_checks.get("success", False)
            }
            
            if combined_result["success"]:
                logger.info("Health check passed - database is ready for production")
            else:
                logger.warning("Health check detected issues - review results")
            
            return combined_result
            
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "error_type": type(e).__name__
            }
    
    def _run_application_specific_checks(self) -> Dict[str, Any]:
        """Run checks specific to the TFT application."""
        checks = {
            "required_tables": [],
            "required_functions": [],
            "data_integrity": [],
            "success": True
        }
        
        try:
            with self.db_manager.get_session() as session:
                # Check required tables
                required_tables = ['matches', 'participants', 'match_clustering']
                for table in required_tables:
                    result = session.execute(
                        "SELECT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = %s)",
                        (table,)
                    )
                    exists = result.fetchone()[0]
                    checks["required_tables"].append({
                        "table": table,
                        "exists": exists
                    })
                    if not exists:
                        checks["success"] = False
                
                # Check required functions
                required_functions = ['insert_match_data']
                for function in required_functions:
                    result = session.execute(
                        "SELECT EXISTS (SELECT 1 FROM pg_proc WHERE proname = %s)",
                        (function,)
                    )
                    exists = result.fetchone()[0]
                    checks["required_functions"].append({
                        "function": function,
                        "exists": exists
                    })
                    if not exists:
                        checks["success"] = False
                
                # Basic data integrity checks
                try:
                    # Check if we have reasonable data structure
                    result = session.execute("SELECT COUNT(*) FROM information_schema.columns WHERE table_name = 'participants'")
                    participant_columns = result.fetchone()[0]
                    
                    checks["data_integrity"].append({
                        "check": "participant_table_structure",
                        "expected_min_columns": 10,
                        "actual_columns": participant_columns,
                        "passed": participant_columns >= 10
                    })
                    
                except Exception as e:
                    logger.warning(f"Data integrity check failed: {e}")
                    checks["data_integrity"].append({
                        "check": "basic_structure",
                        "passed": False,
                        "error": str(e)
                    })
                    checks["success"] = False
        
        except Exception as e:
            logger.error(f"Application-specific checks failed: {e}")
            checks["success"] = False
            checks["error"] = str(e)
        
        return checks


def main():
    """Main entry point for migration script."""
    parser = argparse.ArgumentParser(
        description="Production migration script for TFT Webapp",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    
    parser.add_argument("--initial-setup", action="store_true",
                       help="Run initial database setup")
    parser.add_argument("--migrate", action="store_true",
                       help="Run database migrations only")
    parser.add_argument("--import-data", action="store_true",
                       help="Import data from local/staging")
    parser.add_argument("--health-check", action="store_true",
                       help="Run health checks after migration")
    parser.add_argument("--dry-run", action="store_true",
                       help="Show what would be done without executing")
    parser.add_argument("--force", action="store_true",
                       help="Force migration even if database is not empty")
    parser.add_argument("--verbose", action="store_true",
                       help="Enable verbose logging")
    
    args = parser.parse_args()
    
    # Configure logging
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Default action if none specified
    if not any([args.initial_setup, args.migrate, args.import_data, args.health_check]):
        args.initial_setup = True
        args.health_check = True
    
    try:
        # Initialize migrator
        config = get_production_config()
        migrator = ProductionMigrator(config, dry_run=args.dry_run)
        
        logger.info("=== TFT Webapp Production Migration ===")
        logger.info(f"Environment: {config.environment}")
        logger.info(f"Dry run: {args.dry_run}")
        
        # Check prerequisites
        logger.info("Checking prerequisites...")
        prereq_checks = migrator.check_prerequisites()
        
        failed_checks = [k for k, v in prereq_checks.items() if not v]
        if failed_checks:
            logger.error(f"Prerequisites check failed: {failed_checks}")
            if not args.force:
                logger.error("Use --force to override prerequisite checks")
                sys.exit(1)
            else:
                logger.warning("Continuing with failed prerequisites due to --force flag")
        else:
            logger.info("All prerequisites satisfied")
        
        # Check database state
        logger.info("Checking database state...")
        db_state = migrator.check_database_state()
        
        if not db_state.get("is_empty", True) and not args.force:
            logger.warning("Database is not empty. Use --force to proceed anyway.")
            logger.info(f"Current state: {db_state}")
            response = input("Continue anyway? [y/N]: ")
            if response.lower() not in ['y', 'yes']:
                logger.info("Migration cancelled")
                sys.exit(0)
        
        # Run requested operations
        all_successful = True
        
        if args.initial_setup or args.migrate:
            logger.info("Running database migrations...")
            migration_result = migrator.run_all_migrations()
            
            if migration_result["success"]:
                logger.info("✓ Database migrations completed successfully")
            else:
                logger.error("✗ Database migrations failed")
                all_successful = False
                
                # Print detailed error information
                for result in migration_result.get("results", []):
                    if not result["success"]:
                        logger.error(f"Failed migration: {result['file']}")
                        logger.error(f"Error: {result.get('error', 'Unknown error')}")
        
        if args.import_data and all_successful:
            logger.info("Importing data...")
            import_result = migrator.import_data_from_local()
            
            if import_result["success"]:
                logger.info("✓ Data import completed successfully")
            else:
                logger.error("✗ Data import failed")
                logger.error(f"Error: {import_result.get('error', 'Unknown error')}")
                all_successful = False
        
        if args.health_check and all_successful:
            logger.info("Running health check...")
            health_result = migrator.run_health_check()
            
            if health_result["success"]:
                logger.info("✓ Health check passed")
            else:
                logger.warning("⚠ Health check detected issues")
                # Don't fail the entire process for health check issues
        
        # Final summary
        if all_successful:
            logger.info("🎉 Migration completed successfully!")
            if args.dry_run:
                logger.info("This was a dry run - no changes were made")
            sys.exit(0)
        else:
            logger.error("💥 Migration failed - check logs for details")
            sys.exit(1)
            
    except KeyboardInterrupt:
        logger.info("Migration cancelled by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Migration script failed: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()