from sqlalchemy import create_engine, text

# No host or password: connects over the local Unix socket as your Linux user,
# the same way `psql ladder` does.
DATABASE_URL = "postgresql+psycopg:///ladder"

# echo=True logs every SQL statement SQLAlchemy sends, so nothing is hidden.
engine = create_engine(DATABASE_URL, echo=True)


if __name__ == "__main__":
    with engine.connect() as conn:
        result = conn.execute(text("SELECT 1"))
        print(result.scalar_one())
