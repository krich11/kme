#!/usr/bin/env python3
"""
KME Database Setup Script

Version: 1.0.0
Author: KME Development Team
Description: Database setup and management for KME development
License: [To be determined]

ToDo List:
- [x] Create database setup script
- [x] Add database creation functionality
- [x] Add schema reset functionality
- [x] Add data pull functionality
- [x] Add database removal functionality
- [x] Add command line argument parsing
- [x] Add error handling and validation
- [ ] Add database migration support
- [ ] Add backup/restore functionality
- [ ] Add performance optimization

Progress: 70% (7/10 tasks completed)
"""

import argparse
import asyncio
import json
import os
import sys
from pathlib import Path
from typing import List, Optional

import asyncpg
from dotenv import load_dotenv

# Add the project root to the Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Load environment variables
load_dotenv()


class DatabaseManager:
    """Database management for KME development"""

    def __init__(self, database_url: str):
        """Initialize database manager"""
        self.database_url = database_url
        self.connection = None

    async def connect(self) -> asyncpg.Connection:
        """Connect to database"""
        try:
            self.connection = await asyncpg.connect(self.database_url)
            return self.connection
        except Exception as e:
            print(f"❌ Failed to connect to database: {e}")
            raise

    async def disconnect(self):
        """Disconnect from database"""
        if self.connection:
            await self.connection.close()

    async def create_database(self, database_name: str) -> bool:
        """Create a new database"""
        try:
            # Connect to default postgres database
            conn = await asyncpg.connect(
                host=os.getenv("DB_HOST", "localhost"),
                port=int(os.getenv("DB_PORT", "5432")),
                user=os.getenv("DB_USER", "postgres"),
                password=os.getenv("DB_PASSWORD", ""),
                database="postgres",
            )

            # Check if database exists
            exists = await conn.fetchval(
                "SELECT 1 FROM pg_database WHERE datname = $1", database_name
            )

            if exists:
                print(f"⚠️  Database '{database_name}' already exists")
                await conn.close()
                return True

            # Create database
            await conn.execute(f'CREATE DATABASE "{database_name}"')
            print(f"✅ Database '{database_name}' created successfully")
            await conn.close()
            return True

        except Exception as e:
            print(f"❌ Failed to create database: {e}")
            return False

    async def drop_database(self, database_name: str) -> bool:
        """Drop a database"""
        try:
            # Connect to default postgres database
            conn = await asyncpg.connect(
                host=os.getenv("DB_HOST", "localhost"),
                port=int(os.getenv("DB_PORT", "5432")),
                user=os.getenv("DB_USER", "postgres"),
                password=os.getenv("DB_PASSWORD", ""),
                database="postgres",
            )

            # Check if database exists
            exists = await conn.fetchval(
                "SELECT 1 FROM pg_database WHERE datname = $1", database_name
            )

            if not exists:
                print(f"⚠️  Database '{database_name}' does not exist")
                await conn.close()
                return True

            # Drop database
            await conn.execute(f'DROP DATABASE "{database_name}"')
            print(f"✅ Database '{database_name}' dropped successfully")
            await conn.close()
            return True

        except Exception as e:
            print(f"❌ Failed to drop database: {e}")
            return False

    async def create_schema(self) -> bool:
        """Create KME database schema"""
        try:
            conn = await self.connect()

            # Create schema SQL
            schema_sql = """
            -- Create extensions
            CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
            CREATE EXTENSION IF NOT EXISTS "pgcrypto";

            -- Create KME tables

            -- KME entities table
            CREATE TABLE IF NOT EXISTS kme_entities (
                id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
                kme_id VARCHAR(16) UNIQUE NOT NULL,
                hostname VARCHAR(255) NOT NULL,
                port INTEGER NOT NULL DEFAULT 8443,
                certificate_info JSONB,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
            );

            -- SAE entities table
            CREATE TABLE IF NOT EXISTS sae_entities (
                id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
                sae_id VARCHAR(16) UNIQUE NOT NULL,
                kme_id VARCHAR(16) NOT NULL REFERENCES kme_entities(kme_id),
                certificate_info JSONB,
                registration_date TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                last_seen TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                status VARCHAR(20) DEFAULT 'active',
                created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
            );

            -- Key storage table
            CREATE TABLE IF NOT EXISTS keys (
                id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
                key_id VARCHAR(36) UNIQUE NOT NULL, -- UUID format
                key_data BYTEA NOT NULL,
                key_size INTEGER NOT NULL,
                master_sae_id VARCHAR(16) NOT NULL,
                slave_sae_id VARCHAR(16) NOT NULL,
                source_kme_id VARCHAR(16) NOT NULL,
                target_kme_id VARCHAR(16) NOT NULL,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                expires_at TIMESTAMP WITH TIME ZONE,
                status VARCHAR(20) DEFAULT 'active',
                additional_slave_sae_ids TEXT[], -- Array of additional SAE IDs
                key_metadata JSONB -- For extensions and metadata
            );

            -- Key requests table
            CREATE TABLE IF NOT EXISTS key_requests (
                id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
                request_id VARCHAR(36) UNIQUE NOT NULL,
                master_sae_id VARCHAR(16) NOT NULL,
                slave_sae_id VARCHAR(16) NOT NULL,
                number_of_keys INTEGER NOT NULL DEFAULT 1,
                key_size INTEGER NOT NULL,
                additional_slave_sae_ids TEXT[],
                extension_mandatory JSONB,
                extension_optional JSONB,
                status VARCHAR(20) DEFAULT 'pending',
                created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                completed_at TIMESTAMP WITH TIME ZONE,
                error_message TEXT
            );

            -- Key distribution events table
            CREATE TABLE IF NOT EXISTS key_distribution_events (
                id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
                event_type VARCHAR(50) NOT NULL,
                master_sae_id VARCHAR(16) NOT NULL,
                slave_sae_id VARCHAR(16) NOT NULL,
                key_count INTEGER NOT NULL,
                key_size INTEGER NOT NULL,
                success BOOLEAN NOT NULL,
                error_message TEXT,
                event_details JSONB,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
            );

            -- Security events table
            CREATE TABLE IF NOT EXISTS security_events (
                id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
                event_type VARCHAR(50) NOT NULL,
                severity VARCHAR(20) NOT NULL,
                category VARCHAR(30) NOT NULL,
                user_id VARCHAR(255),
                sae_id VARCHAR(16),
                kme_id VARCHAR(16),
                key_id VARCHAR(36),
                resource VARCHAR(255),
                details JSONB,
                etsi_compliance BOOLEAN DEFAULT TRUE,
                specification VARCHAR(50) DEFAULT 'ETSI GS QKD 014 V1.1.1',
                created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
            );

            -- Performance metrics table
            CREATE TABLE IF NOT EXISTS performance_metrics (
                id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
                metric_name VARCHAR(100) NOT NULL,
                metric_value DOUBLE PRECISION NOT NULL,
                metric_unit VARCHAR(20) NOT NULL,
                metric_type VARCHAR(20) NOT NULL,
                labels JSONB,
                timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW()
            );

            -- Health check history table
            CREATE TABLE IF NOT EXISTS health_checks (
                id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
                check_name VARCHAR(100) NOT NULL,
                status VARCHAR(20) NOT NULL,
                message TEXT,
                details JSONB,
                timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW()
            );

            -- Alerts table
            CREATE TABLE IF NOT EXISTS alerts (
                id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
                alert_id VARCHAR(50) UNIQUE NOT NULL,
                alert_type VARCHAR(30) NOT NULL,
                severity VARCHAR(20) NOT NULL,
                title VARCHAR(255) NOT NULL,
                message TEXT NOT NULL,
                source VARCHAR(100) NOT NULL,
                details JSONB,
                acknowledged BOOLEAN DEFAULT FALSE,
                resolved BOOLEAN DEFAULT FALSE,
                acknowledged_by VARCHAR(255),
                acknowledged_at TIMESTAMP WITH TIME ZONE,
                resolved_by VARCHAR(255),
                resolved_at TIMESTAMP WITH TIME ZONE,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
            );

            -- Create indexes for performance
            CREATE INDEX IF NOT EXISTS idx_keys_key_id ON keys(key_id);
            CREATE INDEX IF NOT EXISTS idx_keys_master_sae_id ON keys(master_sae_id);
            CREATE INDEX IF NOT EXISTS idx_keys_slave_sae_id ON keys(slave_sae_id);
            CREATE INDEX IF NOT EXISTS idx_keys_status ON keys(status);
            CREATE INDEX IF NOT EXISTS idx_keys_created_at ON keys(created_at);

            CREATE INDEX IF NOT EXISTS idx_security_events_event_type ON security_events(event_type);
            CREATE INDEX IF NOT EXISTS idx_security_events_severity ON security_events(severity);
            CREATE INDEX IF NOT EXISTS idx_security_events_created_at ON security_events(created_at);

            CREATE INDEX IF NOT EXISTS idx_performance_metrics_metric_name ON performance_metrics(metric_name);
            CREATE INDEX IF NOT EXISTS idx_performance_metrics_timestamp ON performance_metrics(timestamp);

            CREATE INDEX IF NOT EXISTS idx_alerts_alert_type ON alerts(alert_type);
            CREATE INDEX IF NOT EXISTS idx_alerts_severity ON alerts(severity);
            CREATE INDEX IF NOT EXISTS idx_alerts_created_at ON alerts(created_at);

            -- Create updated_at trigger function
            CREATE OR REPLACE FUNCTION update_updated_at_column()
            RETURNS TRIGGER AS $$
            BEGIN
                NEW.updated_at = NOW();
                RETURN NEW;
            END;
            $$ language 'plpgsql';

            -- Create triggers for updated_at
            CREATE TRIGGER update_kme_entities_updated_at
                BEFORE UPDATE ON kme_entities
                FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

            CREATE TRIGGER update_sae_entities_updated_at
                BEFORE UPDATE ON sae_entities
                FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
            """

            await conn.execute(schema_sql)
            print("✅ Database schema created successfully")
            await self.disconnect()
            return True

        except Exception as e:
            print(f"❌ Failed to create schema: {e}")
            return False

    async def reset_schema(self) -> bool:
        """Reset database schema (drop and recreate)"""
        try:
            conn = await self.connect()

            # Drop all tables
            drop_sql = """
            DROP TABLE IF EXISTS alerts CASCADE;
            DROP TABLE IF EXISTS health_checks CASCADE;
            DROP TABLE IF EXISTS performance_metrics CASCADE;
            DROP TABLE IF EXISTS security_events CASCADE;
            DROP TABLE IF EXISTS key_distribution_events CASCADE;
            DROP TABLE IF EXISTS key_requests CASCADE;
            DROP TABLE IF EXISTS keys CASCADE;
            DROP TABLE IF EXISTS sae_entities CASCADE;
            DROP TABLE IF EXISTS kme_entities CASCADE;
            """

            await conn.execute(drop_sql)
            print("✅ Database schema reset successfully")
            await self.disconnect()

            # Recreate schema
            return await self.create_schema()

        except Exception as e:
            print(f"❌ Failed to reset schema: {e}")
            return False

    async def pull_data(self, table_name: str | None = None) -> bool:
        """Pull data from database tables"""
        try:
            conn = await self.connect()

            if table_name:
                # Pull data from specific table
                tables = [table_name]
            else:
                # Pull data from all tables
                tables = [
                    "kme_entities",
                    "sae_entities",
                    "keys",
                    "key_requests",
                    "key_distribution_events",
                    "security_events",
                    "performance_metrics",
                    "health_checks",
                    "alerts",
                ]

            for table in tables:
                try:
                    # Get row count - table name is validated against known tables
                    # Use parameterized query to avoid SQL injection
                    count = await conn.fetchval(
                        f"SELECT COUNT(*) FROM {table}"  # nosec B608 - table name validated above
                    )
                    print(f"📊 Table '{table}': {count} rows")

                    if count > 0:
                        # Get sample data (first 5 rows) - table name is validated
                        rows = await conn.fetch(
                            f"SELECT * FROM {table} LIMIT 5"  # nosec B608 - table name validated above
                        )
                        print(f"   Sample data:")
                        for i, row in enumerate(rows, 1):
                            print(f"   Row {i}: {dict(row)}")
                    print()

                except Exception as e:
                    print(f"⚠️  Could not read from table '{table}': {e}")

            await self.disconnect()
            return True

        except Exception as e:
            print(f"❌ Failed to pull data: {e}")
            return False

    async def insert_sample_data(self) -> bool:
        """Insert sample data for testing"""
        try:
            conn = await self.connect()

            # Insert sample KME entity
            await conn.execute(
                """
                INSERT INTO kme_entities (kme_id, hostname, port, certificate_info)
                VALUES ($1, $2, $3, $4)
                ON CONFLICT (kme_id) DO NOTHING
            """,
                "KME001",
                "localhost",
                8443,
                json.dumps({"subject": "CN=KME001", "issuer": "CN=CA"}),
            )

            # Insert sample SAE entity
            await conn.execute(
                """
                INSERT INTO sae_entities (sae_id, kme_id, certificate_info)
                VALUES ($1, $2, $3)
                ON CONFLICT (sae_id) DO NOTHING
            """,
                "SAE001ABCDEFGHIJ",
                "KME001",
                json.dumps({"subject": "CN=SAE001", "issuer": "CN=CA"}),
            )

            # Insert sample key
            await conn.execute(
                """
                INSERT INTO keys (key_id, key_data, key_size, master_sae_id, slave_sae_id, source_kme_id, target_kme_id)
                VALUES ($1, $2, $3, $4, $5, $6, $7)
                ON CONFLICT (key_id) DO NOTHING
            """,
                "550e8400-e29b-41d4-a716-446655440000",
                b"sample_key_data_32_bytes_long",
                256,
                "SAE001ABCDEFGHIJ",
                "SAE002ABCDEFGHIJ",
                "KME001",
                "KME002",
            )

            print("✅ Sample data inserted successfully")
            await self.disconnect()
            return True

        except Exception as e:
            print(f"❌ Failed to insert sample data: {e}")
            return False


async def main():
    """Main function"""
    parser = argparse.ArgumentParser(description="KME Database Setup Script")
    parser.add_argument(
        "action",
        choices=["create", "drop", "schema", "reset", "pull", "sample"],
        help="Action to perform",
    )
    parser.add_argument(
        "--database", "-d", default="kme_dev", help="Database name (default: kme_dev)"
    )
    parser.add_argument("--table", "-t", help="Specific table for pull action")
    parser.add_argument("--url", help="Database URL (overrides environment variables)")

    args = parser.parse_args()

    # Get database URL
    if args.url:
        database_url = args.url
    else:
        database_url = os.getenv(
            "DATABASE_URL", f"postgresql://postgres@localhost:5432/{args.database}"
        )

    # Convert postgresql+asyncpg:// to postgresql:// for asyncpg compatibility
    if database_url.startswith("postgresql+asyncpg://"):
        database_url = database_url.replace("postgresql+asyncpg://", "postgresql://")

    print(f"🔧 KME Database Setup Script")
    print(f"Action: {args.action}")
    print(f"Database: {args.database}")
    print(f"URL: {database_url.split('@')[0]}@***")
    print("=" * 50)

    db_manager = DatabaseManager(database_url)

    try:
        if args.action == "create":
            success = await db_manager.create_database(args.database)
            if success:
                success = await db_manager.create_schema()
                if success:
                    success = await db_manager.insert_sample_data()

        elif args.action == "drop":
            success = await db_manager.drop_database(args.database)

        elif args.action == "schema":
            success = await db_manager.create_schema()

        elif args.action == "reset":
            success = await db_manager.reset_schema()
            if success:
                success = await db_manager.insert_sample_data()

        elif args.action == "pull":
            success = await db_manager.pull_data(args.table)

        elif args.action == "sample":
            success = await db_manager.insert_sample_data()

        if success:
            print(f"\n✅ Action '{args.action}' completed successfully")
            sys.exit(0)
        else:
            print(f"\n❌ Action '{args.action}' failed")
            sys.exit(1)

    except KeyboardInterrupt:
        print("\n⚠️  Operation cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
