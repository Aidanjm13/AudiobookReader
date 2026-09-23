# a script for getting the piper voices
import requests
import json
import os
from fileHandling import getAppdataFolderPath

VOICES_URL = "https://huggingface.co/rhasspy/piper-voices/resolve/main/voices.json"
VOICES_DIR = os.path.join(getAppdataFolderPath(), "voices")
FILE_DIR = os.path.join(VOICES_DIR, "voices.json")

#gets the list of voices from the hugging face website and updates the list of existing voices
def refreshPiperVoicesJSON():
    print("Fetching the latest voices from Hugging Face...")
    try:
        response = requests.get(VOICES_URL, timeout=10)
        response.raise_for_status() # Raise an error for bad status codes
        
        # Parse the JSON and extract just the string keys
        voices_data = response.json()
        voice_strings = list(voices_data.keys())
        
        # Sort them alphabetically for a cleaner UI dropdown
        voice_strings.sort()

        if not os.path.exists(VOICES_DIR):
                os.makedirs(VOICES_DIR, exist_ok=True)
        # Save to the local file
        with open(FILE_DIR, 'w', encoding='utf-8') as f:
            json.dump(voice_strings, f, indent=4)
            
        print(f"Success! Saved {len(voice_strings)} voices.")
        return voice_strings
        
    except requests.exceptions.RequestException as e:
        print(f"Network error while refreshing voices: {e}")
        # In a real app, you might want to show a UI popup here
        return None


def parsePiperVoiceString(voice_string: str):
    # 1. Split by hyphen: "en_US-amy-medium" -> ["en_US", "amy", "medium"]
    parts = voice_string.split("-")
    
    # Handle standard 3-part names, with a fallback just in case a speaker name has a hyphen
    voice_code = parts[0]
    quality = parts[-1]
    speaker = "-".join(parts[1:-1]) 
    
    # 2. Split the locale by underscore: "en_US" -> ["en", "US"]
    locale_parts = voice_code.split("_")
    lang = locale_parts[0]
    
    # Some voices might theoretically lack a region, so we safeguard against index errors
    region = locale_parts[1] if len(locale_parts) > 1 else ""
    
    return lang, region, speaker, quality

#gets the voices from the JSON file, if they dont exist, refresh them
def loadVoices():
    if not os.path.exists(FILE_DIR):
        print("No local cache found. Performing initial download...")
        return refreshPiperVoicesJSON()
        
    try:
        with open(FILE_DIR, 'r', encoding='utf-8') as f:
            voice_strings = json.load(f)
            return voice_strings
    except json.JSONDecodeError:
        print("Cache file is corrupted. Re-downloading...")
        return refreshPiperVoicesJSON()