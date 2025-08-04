# KME Database Manager

A comprehensive database management tool for the KME (Key Management Entity) system that provides interactive database browsing, management, and maintenance capabilities.

## Features

### 🔍 Database Browsing
- **Browse Database**: View all tables with row counts
- **Table Structure**: View column definitions, data types, and constraints
- **Table Data**: Browse actual data with configurable row limits (10, 50, 100 rows)
- **Database Statistics**: Get overview of total tables and rows

### 🛠️ Table Management
- **Truncate Tables**: Remove all data while preserving table structure
- **Drop Tables**: Completely remove tables and their data
- **Safe Confirmation**: All destructive operations require explicit confirmation

### 🗄️ Database Operations
- **Reset Database**: Drop all tables and data (complete reset)
- **Recreate Schema**: Reset database and recreate all tables from models
- **Schema Management**: Automatic table creation from SQLAlchemy models

### 📊 Data Export
- **JSON Export**: Export table data to JSON files
- **Configurable Limits**: Export up to 1000 rows per table
- **Metadata Included**: Export includes table name, timestamp, and row count

## Usage

### From Admin Menu
```bash
# Launch the admin menu
./admin/kme-admin-menu.sh

# Select option 11: Database Manager
```

### Direct Execution
```bash
# Run directly
python admin/database_manager.py

# With custom config
python admin/database_manager.py --config /path/to/config.env
```

## Menu Structure

### Main Menu
1. **Browse Database** - Explore tables and data
2. **Table Management** - Manage individual tables
3. **Database Operations** - High-level database operations
4. **Export Data** - Export table data to files
5. **Database Statistics** - View database overview
6. **Quit** - Exit the tool

### Browse Database
- List all tables with row counts
- Select table to browse
- View table structure (columns, types, constraints)
- Browse data with different row limits

### Table Management
- List all tables
- Select table to manage
- Truncate table (remove data)
- Drop table (remove completely)

### Database Operations
- Reset database (drop all tables)
- Recreate schema (reset + recreate tables)
- View database statistics

### Export Data
- List all tables
- Select table to export
- Specify export filename
- Export to JSON format

## Safety Features

### Confirmation Prompts
All destructive operations require explicit confirmation:

- **Truncate Table**: Type `YES` to confirm
- **Drop Table**: Type `DELETE` to confirm
- **Reset Database**: Type `RESET` to confirm
- **Recreate Schema**: Type `RECREATE` to confirm

### Error Handling
- Graceful error handling for database connection issues
- Detailed error messages for failed operations
- Safe rollback on operation failures

## Configuration

The database manager uses the same configuration as the main KME application:

- **Environment Variables**: Standard KME environment variables
- **Database URL**: Configured via `DATABASE_URL` or `KME_DATABASE_URL`
- **Config File**: Support for custom configuration files

## Dependencies

- **SQLAlchemy**: Database ORM and inspection
- **Click**: Command-line interface framework
- **Structlog**: Structured logging
- **AsyncPG**: PostgreSQL async driver

## Examples

### Browse a Table
```
1. Select "Browse Database"
2. Choose table from list
3. Select "Browse data (first 10 rows)"
4. View formatted table data
```

### Export Table Data
```
1. Select "Export Data"
2. Choose table to export
3. Enter filename (or use default)
4. Data exported to JSON file
```

### Reset Database
```
1. Select "Database Operations"
2. Choose "Reset database"
3. Type 'RESET' to confirm
4. All tables and data removed
```

### Recreate Schema
```
1. Select "Database Operations"
2. Choose "Recreate schema"
3. Type 'RECREATE' to confirm
4. Database reset and tables recreated
```

## Security Notes

- **Production Use**: Exercise extreme caution in production environments
- **Backup**: Always backup database before destructive operations
- **Permissions**: Ensure proper database permissions for all operations
- **Network Access**: Database manager connects directly to database

## Troubleshooting

### Connection Issues
- Verify database URL configuration
- Check database server status
- Ensure proper network connectivity
- Verify database user permissions

### Permission Errors
- Check database user privileges
- Verify table ownership
- Ensure proper schema access

### Import Errors
- Verify all dependencies installed
- Check Python path configuration
- Ensure virtual environment activated

## Development

The database manager is built with:
- **Modular Design**: Separate classes for database operations and CLI
- **Async Support**: Async database operations where appropriate
- **Extensible**: Easy to add new features and operations
- **Type Hints**: Full type annotation support
