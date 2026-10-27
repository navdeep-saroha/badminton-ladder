from collections.abc import Iterator

from sqlalchemy import create_engine, text
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column


DATABASE_URL = "postgresql+psycopg:///ladder"

# echo=True logs every SQL statement SQLAlchemy sends, so nothing is hidden.
engine = create_engine(DATABASE_URL, echo=True)


class Base(DeclarativeBase):
    pass


# Maps the existing `players` table to a Python class. schema.sql owns the table
# and its constraints; this class only tells SQLAlchemy which columns exist.
class PlayerRow(Base):
    __tablename__ = "players"

    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str]
    name: Mapped[str]
    rank: Mapped[int]


def get_session() -> Iterator[Session]:
    """One session per request, closed when the request finishes."""
    with Session(engine) as session:
        yield session


if __name__ == "__main__":
    with engine.connect() as conn:
        result = conn.execute(text("SELECT 1"))
        print(result.scalar_one())
