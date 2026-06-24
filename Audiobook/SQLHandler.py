from sqlalchemy import create_engine, ForeignKey, String, Integer, DateTime
from sqlalchemy.orm import declarative_base, Mapped, mapped_column, relationship, sessionmaker
from datetime import datetime
from typing import List, Optional

engine = create_engine("sqlite:///app.db")
Base = declarative_base()
Session = sessionmaker(bind=engine)

class Book(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    author: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    last_accessed: Mapped[datetime] = mapped_column(index=True)
    position: Mapped[int] = mapped_column(Integer)
    voice: Mapped[str] = mapped_column(String(100))
    speed: Mapped[int] = mapped_column(Integer)

Base.metadata.create_all(engine)