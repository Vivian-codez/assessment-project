# Docstring explaining Database table creation script.
"""Database table creation script."""

# Import module os
import os
# Import module sys
import sys

# Ensure backend root is on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Import engine, Base from app.core.database
from app.core.database import engine, Base
# Import module app.models  # noqa
import app.models  # noqa


# Define function init_db
def init_db():
    # Print console output: print("Creating all database tables...")
    print("Creating all database tables...")
    # Execute statement: Base.metadata.create_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    # Print console output: print("Database tables created successfully!")
    print("Database tables created successfully!")


# Check if condition: __name__ == "__main__"
if __name__ == "__main__":
    # Execute statement: init_db()
    init_db()
