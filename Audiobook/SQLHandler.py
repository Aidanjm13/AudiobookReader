from sqlalchemy import create_engine, ForeignKey, String, Integer, DateTime
from sqlalchemy.orm import declarative_base, Mapped, mapped_column, relationship, sessionmaker
from datetime import datetime
from typing import List, Optional

engine = create_engine("sqlite:///app.db")
Base = declarative_base()
Session = sessionmaker(bind=engine)

#current data for a book
class Book(Base):
    __tablename__ = "books"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    file_type: Mapped[str] = mapped_column(String(100), unique=False, index=False) #the file type epub, pdf, text?
    file_path: Mapped[str] = mapped_column(String(4096), unique=True, index=True) #the local filepath of the book file
    image_path: Mapped[str] = mapped_column(String(4096), unique=True, index=True) #the local filepath of the books cover image
    title: Mapped[str] = mapped_column(String(100), unique=False, index=True) #title of the book
    author: Mapped[str] = mapped_column(String(100), unique=False, index=True) #author of the book
    language: Mapped[str] = mapped_column(String(100), unique=False, index=True) #the language the book is written in
    last_accessed: Mapped[datetime] = mapped_column(index=True, unique=False) #when the book was last accessed
    position: Mapped[int] = mapped_column(String(100), unique=False) #the position you are at in the book for epub: "chapter:word" 

#settings presets, will allow for multiple presets to swap between
class Settings(Base):
    __tablename__ = "settings"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=False, index=True)
    speed: Mapped[int] = mapped_column(Integer, unique=False)
    voice: Mapped[str] = mapped_column(String(100), unique=False, index=True)

Base.metadata.create_all(engine)