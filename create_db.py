from db.database import engine
from db.models import Base


def main():
    """Create all tables defined on Base against the configured engine."""
    Base.metadata.create_all(bind=engine)
    try:
        # engine.url is a sqlalchemy.engine.URL-like object; str() yields the DB URL
        print("Database and tables created. Engine URL:", str(engine.url))
    except Exception:
        print("Database and tables created.")


if __name__ == "__main__":
    main()
