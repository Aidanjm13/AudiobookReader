import os
import json
from datetime import datetime

def getAppdataFolderPath():
    appdata = os.getenv('LOCALAPPDATA')
    company = "Aidanjm13"
    app_name = "AudiobookReader"
    folder_path = os.path.join(appdata, company, app_name)
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
