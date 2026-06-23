import os
import json
from datetime import datetime

def getAppdataFolderPath():
    appdata = os.getenv('LOCALAPPDATA')

    company = "Aidanjm13"

    app_name = "AudiobookReader"

    folder_path = os.path.join(appdata, company, app_name)
    return folder_path

def saveNewBook(path):
    file_name = os.path.basename(path)

    folder_path = os.path.join(getAppdataFolderPath(), os.path.splitext(file_name)[0].lower())

    if not os.path.exists(folder_path):
        os.makedirs(folder_path)

    destination_path = os.path.join(folder_path, file_name)

    with open(path, 'rb') as source_file:
        with open(destination_path, 'wb') as dest_file:
            dest_file.write(source_file.read())
    
    createMetaFile(folder_path, file_name)

    return destination_path

def createMetaFile(folder_path, file_name):
    metaPath = os.path.join(folder_path, file_name + ".meta")

    metadata = {
        "filename": file_name,
        "last_accessed": datetime.now().isoformat(),
        "currentProgress": 0,
        "bookSpeed": 1,
        "voiceType": "default",
        "fontType": "default",
        "fontSize": 1
    }

    with open(metaPath, "w") as f:
        json.dump(metadata, f, indent=2)
    pass