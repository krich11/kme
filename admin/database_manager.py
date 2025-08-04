#!/usr/bin/env python3
"""
Database Manager Tool for KME

A comprehensive database management tool that provides:
- Database browsing and inspection
- Table management (drop, truncate, etc.)
- Database reset and recreation
- Schema management
- Data export/import capabilities
"""

import asyncio
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import asyncpg
import click
import structlog
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import Engine
from sqlalchemy.exc import SQLAlchemyError

# Add the project root to the Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.core.config import get_settings  # noqa: E402
from app.models.sqlalchemy_models import Base  # noqa: E402

logger = structlog.get_logger()


class DatabaseManager:
    """Database management tool for KME"""

    def __init__(self):
        """Initialize database manager"""
        self.settings = get_settings()
        self.engine: Engine | None = None
        self.inspector = None
        self.connection = None

    def connect(self) -> bool:
        """Connect to the database"""
        try:
            # Create SQLAlchemy engine with synchronous driver
            database_url = self.settings.database_url
            # Convert asyncpg URL to psycopg2 for synchronous operations
            if "asyncpg" in database_url:
                database_url = database_url.replace(
                    "postgresql+asyncpg://", "postgresql://"
                )

            self.engine = create_engine(database_url)

            # Test connection
            with self.engine.connect() as conn:
                conn.execute(text("SELECT 1"))

            self.inspector = inspect(self.engine)
            logger.info("Database connection established successfully")
            return True

        except Exception as e:
            logger.error(f"Failed to connect to database: {e}")
            return False

    def disconnect(self):
        """Disconnect from the database"""
        if self.engine:
            self.engine.dispose()
            logger.info("Database connection closed")

    def get_tables(self) -> list[str]:
        """Get list of all tables in the database"""
        try:
            return self.inspector.get_table_names()
        except Exception as e:
            logger.error(f"Failed to get tables: {e}")
            return []

    def get_table_info(self, table_name: str) -> dict[str, Any]:
        """Get detailed information about a table"""
        try:
            info = {
                "name": table_name,
                "columns": self.inspector.get_columns(table_name),
                "primary_keys": self.inspector.get_pk_constraint(table_name),
                "foreign_keys": self.inspector.get_foreign_keys(table_name),
                "indexes": self.inspector.get_indexes(table_name),
            }

            # Get row count
            with self.engine.connect() as conn:
                result = conn.execute(text(f"SELECT COUNT(*) FROM {table_name}"))
                info["row_count"] = result.scalar()

            return info

        except Exception as e:
            logger.error(f"Failed to get table info for {table_name}: {e}")
            return {}

    def browse_table(self, table_name: str, limit: int = 10) -> list[dict[str, Any]]:
        """Browse table data with optional limit"""
        try:
            with self.engine.connect() as conn:
                result = conn.execute(text(f"SELECT * FROM {table_name} LIMIT {limit}"))
                columns = result.keys()
                rows = [dict(zip(columns, row)) for row in result.fetchall()]
                return rows

        except Exception as e:
            logger.error(f"Failed to browse table {table_name}: {e}")
            return []

    def drop_table(self, table_name: str) -> bool:
        """Drop a table from the database"""
        try:
            with self.engine.connect() as conn:
                conn.execute(text(f"DROP TABLE IF EXISTS {table_name} CASCADE"))
                conn.commit()
            logger.info(f"Table {table_name} dropped successfully")
            return True

        except Exception as e:
            logger.error(f"Failed to drop table {table_name}: {e}")
            return False

    def truncate_table(self, table_name: str) -> bool:
        """Truncate a table (remove all data but keep structure)"""
        try:
            with self.engine.connect() as conn:
                conn.execute(text(f"TRUNCATE TABLE {table_name} CASCADE"))
                conn.commit()
            logger.info(f"Table {table_name} truncated successfully")
            return True

        except Exception as e:
            logger.error(f"Failed to truncate table {table_name}: {e}")
            return False

    def reset_database(self) -> bool:
        """Reset the entire database (drop all tables)"""
        try:
            tables = self.get_tables()
            with self.engine.connect() as conn:
                # Disable foreign key checks temporarily
                conn.execute(text("SET session_replication_role = replica"))

                for table in tables:
                    conn.execute(text(f"DROP TABLE IF EXISTS {table} CASCADE"))

                # Re-enable foreign key checks
                conn.execute(text("SET session_replication_role = DEFAULT"))
                conn.commit()

            logger.info(f"Database reset successfully. Dropped {len(tables)} tables.")
            return True

        except Exception as e:
            logger.error(f"Failed to reset database: {e}")
            return False

    def recreate_schema(self) -> bool:
        """Recreate the database schema from models"""
        try:
            # Drop all existing tables
            self.reset_database()

            # Create all tables from models
            Base.metadata.create_all(self.engine)

            logger.info("Database schema recreated successfully")
            return True

        except Exception as e:
            logger.error(f"Failed to recreate schema: {e}")
            return False

    def export_table_data(self, table_name: str, filename: str) -> bool:
        """Export table data to JSON file"""
        try:
            data = self.browse_table(table_name, limit=1000)  # Export up to 1000 rows

            export_data = {
                "table_name": table_name,
                "exported_at": datetime.utcnow().isoformat(),
                "row_count": len(data),
                "data": data,
            }

            with open(filename, "w") as f:
                json.dump(export_data, f, indent=2, default=str)

            logger.info(f"Table {table_name} exported to {filename}")
            return True

        except Exception as e:
            logger.error(f"Failed to export table {table_name}: {e}")
            return False

    def get_database_stats(self) -> dict[str, Any]:
        """Get database statistics"""
        try:
            stats: dict[str, Any] = {
                "total_tables": 0,
                "total_rows": 0,
                "table_details": {},
            }

            tables = self.get_tables()
            stats["total_tables"] = len(tables)

            for table in tables:
                info = self.get_table_info(table)
                table_details: dict[str, Any] = stats["table_details"]
                table_details[table] = {
                    "columns": len(info.get("columns", [])),
                    "rows": info.get("row_count", 0),
                }
                stats["total_rows"] += info.get("row_count", 0)

            return stats

        except Exception as e:
            logger.error(f"Failed to get database stats: {e}")
            return {}


class DatabaseManagerCLI:
    """Command-line interface for database manager"""

    def __init__(self):
        """Initialize CLI"""
        self.db_manager = DatabaseManager()

    def run(self):
        """Run the database manager CLI"""
        print("=" * 60)
        print("  KME Database Manager")
        print("=" * 60)

        # Connect to database
        if not self.db_manager.connect():
            print("❌ Failed to connect to database. Please check your configuration.")
            return

        try:
            while True:
                self.show_main_menu()
        except KeyboardInterrupt:
            print("\n👋 Goodbye!")
        finally:
            self.db_manager.disconnect()

    def show_main_menu(self):
        """Show the main menu"""
        print("\n" + "=" * 40)
        print("  MAIN MENU")
        print("=" * 40)
        print("1.  Browse Database")
        print("2.  Table Management")
        print("3.  Database Operations")
        print("4.  Export Data")
        print("5.  Database Statistics")
        print("q.  Quit")
        print("-" * 40)

        choice = input("Enter your choice: ").strip().lower()

        if choice == "1":
            self.browse_database_menu()
        elif choice == "2":
            self.table_management_menu()
        elif choice == "3":
            self.database_operations_menu()
        elif choice == "4":
            self.export_data_menu()
        elif choice == "5":
            self.show_database_stats()
        elif choice == "q":
            raise KeyboardInterrupt
        else:
            print("❌ Invalid choice. Please try again.")

    def browse_database_menu(self):
        """Browse database menu"""
        while True:
            print("\n" + "=" * 40)
            print("  BROWSE DATABASE")
            print("=" * 40)

            tables = self.db_manager.get_tables()
            if not tables:
                print("No tables found in database.")
                return

            print("Available tables:")
            for i, table in enumerate(tables, 1):
                info = self.db_manager.get_table_info(table)
                row_count = info.get("row_count", 0)
                print(f"{i:2d}. {table} ({row_count} rows)")

            print("0.  Back to main menu")
            print("-" * 40)

            choice = input("Select table to browse (or 0 to go back): ").strip()

            if choice == "0":
                break
            elif choice.isdigit() and 1 <= int(choice) <= len(tables):
                table_name = tables[int(choice) - 1]
                self.browse_table_menu(table_name)
            else:
                print("❌ Invalid choice. Please try again.")

    def browse_table_menu(self, table_name: str):
        """Browse specific table menu"""
        while True:
            print(f"\n" + "=" * 40)
            print(f"  BROWSE TABLE: {table_name}")
            print("=" * 40)

            info = self.db_manager.get_table_info(table_name)
            print(f"Columns: {len(info.get('columns', []))}")
            print(f"Rows: {info.get('row_count', 0)}")
            print(
                f"Primary Keys: {info.get('primary_keys', {}).get('constrained_columns', [])}"
            )

            print("\nOptions:")
            print("1.  View table structure")
            print("2.  Browse data (first 10 rows)")
            print("3.  Browse data (first 50 rows)")
            print("4.  Browse data (first 100 rows)")
            print("0.  Back to table list")
            print("-" * 40)

            choice = input("Enter your choice: ").strip()

            if choice == "0":
                break
            elif choice == "1":
                self.show_table_structure(table_name)
            elif choice in ["2", "3", "4"]:
                limit = int(choice) * 10
                self.show_table_data(table_name, limit)
            else:
                print("❌ Invalid choice. Please try again.")

    def show_table_structure(self, table_name: str):
        """Show table structure"""
        info = self.db_manager.get_table_info(table_name)
        columns = info.get("columns", [])

        print(f"\nTable Structure: {table_name}")
        print("-" * 80)
        print(f"{'Column':<20} {'Type':<20} {'Nullable':<10} {'Default':<15}")
        print("-" * 80)

        for col in columns:
            nullable = "YES" if col.get("nullable", True) else "NO"
            default = str(col.get("default", ""))[:14]
            print(
                f"{col['name']:<20} {str(col['type']):<20} {nullable:<10} {default:<15}"
            )

    def show_table_data(self, table_name: str, limit: int):
        """Show table data"""
        data = self.db_manager.browse_table(table_name, limit)

        if not data:
            print(f"No data found in table {table_name}")
            return

        print(f"\nTable Data: {table_name} (showing {len(data)} rows)")
        print("-" * 100)

        # Show column headers
        columns = list(data[0].keys())
        for col in columns:
            print(f"{col:<20}", end="")
        print()
        print("-" * 100)

        # Show data rows
        for row in data:
            for col in columns:
                value = str(row.get(col, ""))[:18]
                print(f"{value:<20}", end="")
            print()

    def table_management_menu(self):
        """Table management menu"""
        while True:
            print("\n" + "=" * 40)
            print("  TABLE MANAGEMENT")
            print("=" * 40)

            tables = self.db_manager.get_tables()
            if not tables:
                print("No tables found in database.")
                return

            print("Available tables:")
            for i, table in enumerate(tables, 1):
                info = self.db_manager.get_table_info(table)
                row_count = info.get("row_count", 0)
                print(f"{i:2d}. {table} ({row_count} rows)")

            print("0.  Back to main menu")
            print("-" * 40)

            choice = input("Select table to manage (or 0 to go back): ").strip()

            if choice == "0":
                break
            elif choice.isdigit() and 1 <= int(choice) <= len(tables):
                table_name = tables[int(choice) - 1]
                self.manage_table_menu(table_name)
            else:
                print("❌ Invalid choice. Please try again.")

    def manage_table_menu(self, table_name: str):
        """Manage specific table menu"""
        while True:
            print(f"\n" + "=" * 40)
            print(f"  MANAGE TABLE: {table_name}")
            print("=" * 40)

            info = self.db_manager.get_table_info(table_name)
            print(f"Rows: {info.get('row_count', 0)}")

            print("\nOptions:")
            print("1.  Truncate table (remove all data)")
            print("2.  Drop table (remove table completely)")
            print("0.  Back to table list")
            print("-" * 40)

            choice = input("Enter your choice: ").strip()

            if choice == "0":
                break
            elif choice == "1":
                self.confirm_truncate_table(table_name)
            elif choice == "2":
                self.confirm_drop_table(table_name)
            else:
                print("❌ Invalid choice. Please try again.")

    def confirm_truncate_table(self, table_name: str):
        """Confirm table truncation"""
        print(f"\n⚠️  WARNING: This will remove ALL data from table '{table_name}'")
        confirm = input("Are you sure? Type 'YES' to confirm: ").strip()

        if confirm == "YES":
            if self.db_manager.truncate_table(table_name):
                print("✅ Table truncated successfully")
            else:
                print("❌ Failed to truncate table")
        else:
            print("❌ Operation cancelled")

    def confirm_drop_table(self, table_name: str):
        """Confirm table deletion"""
        print(f"\n⚠️  WARNING: This will DELETE the entire table '{table_name}'")
        confirm = input("Are you sure? Type 'DELETE' to confirm: ").strip()

        if confirm == "DELETE":
            if self.db_manager.drop_table(table_name):
                print("✅ Table dropped successfully")
            else:
                print("❌ Failed to drop table")
        else:
            print("❌ Operation cancelled")

    def database_operations_menu(self):
        """Database operations menu"""
        while True:
            print("\n" + "=" * 40)
            print("  DATABASE OPERATIONS")
            print("=" * 40)
            print("1.  Reset database (drop all tables)")
            print("2.  Recreate schema (reset + recreate all tables)")
            print("3.  Show database statistics")
            print("0.  Back to main menu")
            print("-" * 40)

            choice = input("Enter your choice: ").strip()

            if choice == "0":
                break
            elif choice == "1":
                self.confirm_reset_database()
            elif choice == "2":
                self.confirm_recreate_schema()
            elif choice == "3":
                self.show_database_stats()
            else:
                print("❌ Invalid choice. Please try again.")

    def confirm_reset_database(self):
        """Confirm database reset"""
        print("\n⚠️  WARNING: This will DELETE ALL TABLES and ALL DATA")
        print("This operation cannot be undone!")
        confirm = input("Type 'RESET' to confirm: ").strip()

        if confirm == "RESET":
            if self.db_manager.reset_database():
                print("✅ Database reset successfully")
            else:
                print("❌ Failed to reset database")
        else:
            print("❌ Operation cancelled")

    def confirm_recreate_schema(self):
        """Confirm schema recreation"""
        print("\n⚠️  WARNING: This will DELETE ALL TABLES and recreate them")
        print("This operation cannot be undone!")
        confirm = input("Type 'RECREATE' to confirm: ").strip()

        if confirm == "RECREATE":
            if self.db_manager.recreate_schema():
                print("✅ Schema recreated successfully")
            else:
                print("❌ Failed to recreate schema")
        else:
            print("❌ Operation cancelled")

    def export_data_menu(self):
        """Export data menu"""
        while True:
            print("\n" + "=" * 40)
            print("  EXPORT DATA")
            print("=" * 40)

            tables = self.db_manager.get_tables()
            if not tables:
                print("No tables found in database.")
                return

            print("Available tables:")
            for i, table in enumerate(tables, 1):
                info = self.db_manager.get_table_info(table)
                row_count = info.get("row_count", 0)
                print(f"{i:2d}. {table} ({row_count} rows)")

            print("0.  Back to main menu")
            print("-" * 40)

            choice = input("Select table to export (or 0 to go back): ").strip()

            if choice == "0":
                break
            elif choice.isdigit() and 1 <= int(choice) <= len(tables):
                table_name = tables[int(choice) - 1]
                self.export_table_menu(table_name)
            else:
                print("❌ Invalid choice. Please try again.")

    def export_table_menu(self, table_name: str):
        """Export specific table menu"""
        print(f"\n" + "=" * 40)
        print(f"  EXPORT TABLE: {table_name}")
        print("=" * 40)

        filename = input(
            f"Enter filename for export (default: {table_name}_export.json): "
        ).strip()
        if not filename:
            filename = f"{table_name}_export.json"

        if not filename.endswith(".json"):
            filename += ".json"

        if self.db_manager.export_table_data(table_name, filename):
            print(f"✅ Table exported to {filename}")
        else:
            print("❌ Failed to export table")

    def show_database_stats(self):
        """Show database statistics"""
        stats = self.db_manager.get_database_stats()

        print("\n" + "=" * 40)
        print("  DATABASE STATISTICS")
        print("=" * 40)
        print(f"Total Tables: {stats.get('total_tables', 0)}")
        print(f"Total Rows: {stats.get('total_rows', 0)}")

        if stats.get("table_details"):
            print("\nTable Details:")
            print("-" * 50)
            for table, details in stats["table_details"].items():
                print(
                    f"{table:<25} {details['rows']:>8} rows, {details['columns']:>3} columns"
                )

        input("\nPress Enter to continue...")


@click.command()
@click.option("--config", "-c", help="Configuration file path")
def main(config):
    """KME Database Manager CLI"""
    if config:
        os.environ["KME_CONFIG_FILE"] = config

    cli = DatabaseManagerCLI()
    cli.run()


if __name__ == "__main__":
    main()
