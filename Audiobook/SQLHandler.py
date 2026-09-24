from sqlalchemy import create_engine, String, Integer, Float, Boolean
from sqlalchemy.orm import declarative_base, Mapped, mapped_column, relationship, sessionmaker
from datetime import datetime
from fileHandling import getAppdataFolderPath
import os

def getSQLPath():
    appdata_folder = getAppdataFolderPath()
    sql_file_path = os.path.join(appdata_folder, "app.db")
    return sql_file_path


engine = create_engine(f"sqlite:///{getSQLPath()}")
Base = declarative_base()
Session = sessionmaker(bind=engine)

#table
#current data for a book
class Book(Base):
    __tablename__ = "books"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    file_type: Mapped[str] = mapped_column(String(100), unique=False, index=False) #the file type epub, pdf, text?
    file_path: Mapped[str] = mapped_column(String(4096), unique=True, index=True) #the local filepath of the book file
    image_path: Mapped[str] = mapped_column(String(4096), unique=True, index=True, nullable=True) #the local filepath of the books cover image
    title: Mapped[str] = mapped_column(String(100), unique=False, index=True, default="") #title of the book
    author: Mapped[str] = mapped_column(String(100), unique=False, index=True, default="") #author of the book
    language: Mapped[str] = mapped_column(String(100), unique=False, index=True, default="") #the language the book is written in
    last_accessed: Mapped[datetime] = mapped_column(index=True, unique=False) #when the book was last accessed
    chapter: Mapped[int] = mapped_column(Integer) #the chapter you are at in the book for epub, page for pdf
    sentence: Mapped[int] = mapped_column(Integer) #the sentence you are at in the book

#table
#settings presets, will allow for multiple presets to swap between
class Settings(Base):
    __tablename__ = "settings"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=False) #name of the preset
    speed: Mapped[float] = mapped_column(Float, unique=False) #speed of the audiobook reading: 0-3
    volume: Mapped[float] = mapped_column(Float, unique=False) #volume of the audiobook reading: 0-1
    voice_engine: Mapped[str] = mapped_column(String(100), unique=False) #the engine for the model
    voice_model: Mapped[str] = mapped_column(String(100), unique=False) #name of the audiobook voice
    font_size: Mapped[int] = mapped_column(Integer, unique=False) #size of the text
    font_style: Mapped[str] = mapped_column(String(100), unique=False) #name of the text font
    active: Mapped[bool] = mapped_column(Boolean, unique=False)

#creates database tables if needed
def init_db():
    Base.metadata.create_all(engine)

#insert row in books table
def add_book(file_type, file_path, image_path, title, author, language, chapter, sentence):
    """Insert a new Book row and return the created object's id."""
    with Session() as session:
        book = Book(
            file_type=file_type,
            file_path=file_path,
            image_path=image_path,
            title=title,
            author=author,
            language=language,
            last_accessed=datetime.now(),
            chapter = chapter,
            sentence = sentence
        )
        session.add(book)
        session.commit()
        return book.id

def update_book(book_id, **fields):
    """
    Update fields on an existing Book row.
    Usage: update_book(3, title="New Title", position="5:120")
    """
    with Session() as session:
        book = session.get(Book, book_id)
        if book is None:
            raise ValueError(f"No book with id {book_id}")

        for key, value in fields.items():
            setattr(book, key, value)

        session.commit()

def update_book_position(book_id, chapter, position):
    with Session() as session:
        book = session.get(Book, book_id)
        if book is None:
            raise ValueError(f"No book with id {book_id}")
        book.chapter = chapter
        book.sentence = position
        book.last_accessed = datetime.now()
        session.commit()

def delete_book(book_id):
    with Session() as session:
        book = session.get(Book, book_id)
        if book is None:
            return  # already gone, nothing to do
        session.delete(book)
        session.commit()

#insert row in settings table
def add_settings(name, speed, volume, voice_engine, voice_model, font_size, font_style, active):
    with Session() as session:
        settings = Settings(
            name=name,
            speed=speed,
            voice_engine=voice_engine,
            voice_model=voice_model,
            volume=volume,
            font_size=font_size,
            font_style=font_style,
            active=active
        )
        session.add(settings)
        session.commit()
        return settings.id

def delete_settings(settings_id):
    with Session() as session:
        settings = session.get(Settings, settings_id)
        if settings is None:
            return
        session.delete(settings)
        session.commit()

def get_book(book_id):
    """Fetch a single Book by id. Returns None if not found."""
    with Session() as session:
        return session.get(Book, book_id)

#returns a list of book ids, titles, book path, and cover image path for the library
def get_books_by_accessed():
    with Session() as session:
        books = session.query(Book).order_by(Book.last_accessed.desc()).all()
        return [{"id": book.id, "title": book.title, "path": book.file_path, "cover": book.image_path} for book in books]



def get_settings(settings_id):
    """Fetch a single Settings preset by id. Returns None if not found."""
    with Session() as session:
        return session.get(Settings, settings_id)

def num_settings():
    """Return the total number of Settings presets."""
    with Session() as session:
        return session.query(Settings).count()

def get_active_setting():
    """Fetch the currently active Settings preset. Returns None if not found."""
    with Session() as session:
        return session.query(Settings).filter_by(active=True).first()

def update_settings(book_id, **fields):
    """
    Update fields on an existing Settings row.
    Usage: update_settings(3, speed=1.5, volume=0.8)
    """
    with Session() as session:
        settings = session.get(Settings, book_id)
        if settings is None:
            raise ValueError(f"No settings with id {book_id}")

        for key, value in fields.items():
            setattr(settings, key, value)

        session.commit()

