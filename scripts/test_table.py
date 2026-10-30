"""
==============================================================================
Verism AI – Database Table Inspection & Verification Script
Inspects all database tables, columns, constraints, and row counts in
the local PostgreSQL database (or fallback SQLite database).
==============================================================================
"""

# Import sys module for managing runtime path and command line arguments
import sys
# Import os module for interacting with the file system and environment
import os

# Compute the path to the backend directory relative to this script
backend_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "backend")
# Check if the backend path is currently present in sys.path
if backend_path not in sys.path:
    # Prepend backend path to sys.path so app packages can be imported
    sys.path.insert(0, backend_path)

# Import SQLAlchemy inspect utility to examine database schemas and metadata
from sqlalchemy import inspect, text
# Import database engine and declarative Base from the backend core module
from app.core.database import engine, Base
# Import application settings to read the active DATABASE_URL
from app.core.config import settings
# Import all model definitions to register them with SQLAlchemy Base
import app.models  # noqa: F401


def inspect_database_tables():
    """Inspects all tables in the active database engine and prints summary statistics."""
    # Print header banner for database inspection
    print("=" * 70)
    # Print the database connection string currently targeted
    print(f"DATABASE TARGET: {settings.DATABASE_URL}")
    # Print separator line
    print("=" * 70)

    # Create an SQLAlchemy inspector object bound to the active database engine
    inspector = inspect(engine)
    # Retrieve the names of all physical tables currently residing in the database
    physical_tables = inspector.get_table_names()
    # Retrieve the names of all tables defined in SQLAlchemy model metadata
    model_tables = list(Base.metadata.tables.keys())

    # Print section header for registered model tables
    print(f"\n[1] Registered Model Tables ({len(model_tables)} total):")
    # Iterate through each model table defined in the ORM
    for name in sorted(model_tables):
        # Print table name with bullet
        print(f"  • {name}")

    # Print section header for physical database tables
    print(f"\n[2] Physical Database Tables ({len(physical_tables)} total):")
    # Open a connection to execute count queries against each physical table
    with engine.connect() as conn:
        # Iterate through each table discovered in the physical database schema
        for table_name in sorted(physical_tables):
            # Inspect the column definitions for this table
            columns = inspector.get_columns(table_name)
            # Inspect primary key constraints for this table
            pk_constraint = inspector.get_pk_constraint(table_name)
            # Extract primary key column names as a formatted string
            pk_cols = ", ".join(pk_constraint.get("constrained_columns", [])) or "None"
            # Inspect foreign key constraints for this table
            fks = inspector.get_foreign_keys(table_name)
            # Query the current row count in the table
            try:
                # Execute a SELECT COUNT(*) query using SQLAlchemy text()
                result = conn.execute(text(f"SELECT COUNT(*) FROM {table_name}"))
                # Fetch scalar count value
                row_count = result.scalar()
            # Handle cases where table cannot be queried
            except Exception as e:
                # Set row count indicator to error string
                row_count = f"Error: {e}"

            # Print table summary line with row count and primary key details
            print(f"\n  TABLE: {table_name} (Rows: {row_count})")
            # Print primary key column names
            print(f"    - Primary Key: {pk_cols}")
            # Print column count
            print(f"    - Columns ({len(columns)}):")
            # Iterate through columns to print name and data type
            for col in columns:
                # Extract column name
                col_name = col.get("name")
                # Extract column type as string
                col_type = str(col.get("type"))
                # Extract nullable flag
                nullable = "NULL" if col.get("nullable") else "NOT NULL"
                # Print column attribute details indented
                print(f"        • {col_name:<28} {col_type:<20} {nullable}")

            # Check if any foreign key relationships exist on this table
            if fks:
                # Print foreign key header
                print(f"    - Foreign Keys ({len(fks)}):")
                # Iterate through each foreign key constraint
                for fk in fks:
                    # Extract source columns
                    src = ", ".join(fk.get("constrained_columns", []))
                    # Extract target table and target columns
                    ref = f"{fk.get('referred_table')}({', '.join(fk.get('referred_columns', []))})"
                    # Print foreign key mapping
                    print(f"        • {src} -> {ref}")

    # Print completion footer
    print("\n" + "=" * 70)
    # Print status message
    print("Database table inspection completed successfully.")
    # Print footer line
    print("=" * 70)


# Main entry point guard to execute the script when run directly
if __name__ == "__main__":
    # Call the inspection function
    inspect_database_tables()
