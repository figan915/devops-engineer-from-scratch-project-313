from sqlmodel import Field, SQLModel


# Модель ссылки (таблица links)
class Link(SQLModel, table=True):
    __tablename__: str = "links"

    id: int | None = Field(default=None, primary_key=True)
    # short_name должен быть уникальным — это гарантирует БД (UNIQUE)
    short_name: str = Field(index=True, unique=True)
    original_url: str
