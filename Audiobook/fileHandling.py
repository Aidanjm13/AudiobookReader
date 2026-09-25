import os
import sys

def getAppdataFolderPath():
    if sys.platform == "win32":
        base_path = os.environ.get("LOCALAPPDATA")
    else:
        base_path = os.path.expanduser("~/.local/share")
        
    company = "Aidanjm13"
    app_name = "AudiobookReader"
    folder_path = os.path.join(base_path, company, app_name)
    
    # Create the folder (and any missing parent folders) if it doesn't exist
    os.makedirs(folder_path, exist_ok=True)
    
    return folder_path

def getBooksFolderPath():
    appdata_folder = getAppdataFolderPath()
    books_folder = os.path.join(appdata_folder, "books")
    if not os.path.exists(books_folder):
        os.makedirs(books_folder)
    return books_folder

def saveNewBook(path):
    file_name = os.path.basename(path)

    folder_path = os.path.join(getBooksFolderPath(), os.path.splitext(file_name)[0].lower())

    if not os.path.exists(folder_path):
        os.makedirs(folder_path)

    destination_path = os.path.join(folder_path, file_name)

    with open(path, 'rb') as source_file:
        with open(destination_path, 'wb') as dest_file:
            dest_file.write(source_file.read())
    
    return destination_path
