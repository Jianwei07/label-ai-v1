from databases import Database
from sqlalchemy import create_engine, MetaData
from app.core.config import settings

# The `databases` library provides simple async support for the database.
database = Database(settings.DATABASE_URL)

# SQLAlchemy core is used for query building.
metadata = MetaData()

# The engine is used by SQLAlchemy, not directly by our app code with the `databases` library.
# It can be useful for things like initial table creation or migrations.
engine = create_engine(
    settings.DATABASE_URL,
    # connect_args={"check_same_thread": False} # This is needed only for SQLite
)
