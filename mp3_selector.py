import os
import random
import shutil
import unicodedata
import json
import time
from mutagen.easyid3 import EasyID3
from collections import defaultdict
import pythoncom
import win32com.client

# Define the path to the folder with MP3 files
music_folder = r"C:\Users\alexg\Music\temp1"
destination_folder = r"C:\Users\alexg\Music\Temp3"
cache_folder = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cache")  # Pasta cache na raiz do projeto

# Configuration
test_limit = 999999  # Limit of files for the initial test (modifiable)
songs_per_artist = 4  # Number of songs to select per artist in Group 1
max_size_gb = 20  # Maximum total size of files to copy or link, in GB
copy_mode = True  # If True, copy files; if False, create Windows shortcuts (.lnk)
use_cache = True  # If True, use cache when available; if False, always rescan
force_rescan = False  # If True, force rescan even if cache exists

# Convert max size in GB to bytes for comparison
max_size_bytes = max_size_gb * (1024 ** 3)

# Function to normalize text (remove accents and convert to lowercase)
def normalize_text(text):
    text = unicodedata.normalize('NFKD', text).encode('ASCII', 'ignore').decode('ASCII')
    return text.lower()

# Cache management functions
def get_cache_filename(music_folder):
    """Gera nome único do arquivo de cache baseado na pasta de música."""
    folder_hash = abs(hash(music_folder)) % (10 ** 8)
    return os.path.join(cache_folder, f"music_cache_{folder_hash}.json")

def get_folder_modification_time(folder):
    """Obtém o tempo de modificação mais recente da pasta e subpastas."""
    latest_time = 0
    for root, dirs, files in os.walk(folder):
        folder_time = os.path.getmtime(root)
        if folder_time > latest_time:
            latest_time = folder_time
        for file in files:
            if file.lower().endswith('.mp3'):
                file_path = os.path.join(root, file)
                try:
                    file_time = os.path.getmtime(file_path)
                    if file_time > latest_time:
                        latest_time = file_time
                except:
                    continue
    return latest_time

def save_cache(songs, music_folder):
    """Salva a lista de músicas no cache."""
    try:
        if not os.path.exists(cache_folder):
            os.makedirs(cache_folder)
        
        cache_data = {
            "timestamp": time.time(),
            "music_folder": music_folder,
            "folder_mod_time": get_folder_modification_time(music_folder),
            "songs": songs,
            "total_songs": len(songs)
        }
        
        cache_file = get_cache_filename(music_folder)
        with open(cache_file, 'w', encoding='utf-8') as f:
            json.dump(cache_data, f, ensure_ascii=False, indent=2)
        
        print(f"Cache salvo: {cache_file}")
        print(f"Total de músicas em cache: {len(songs)}")
        return True
    except Exception as e:
        print(f"Erro ao salvar cache: {e}")
        return False

def load_cache(music_folder):
    """Carrega a lista de músicas do cache se disponível e válido."""
    try:
        cache_file = get_cache_filename(music_folder)
        
        if not os.path.exists(cache_file):
            print("Arquivo de cache não encontrado.")
            return None
        
        with open(cache_file, 'r', encoding='utf-8') as f:
            cache_data = json.load(f)
        
        # Verifica se o cache é para a mesma pasta
        if cache_data.get("music_folder") != music_folder:
            print("Cache é para uma pasta diferente.")
            return None
        
        # Verifica se a pasta foi modificada desde o cache
        current_mod_time = get_folder_modification_time(music_folder)
        cached_mod_time = cache_data.get("folder_mod_time", 0)
        
        if current_mod_time > cached_mod_time:
            print("Pasta de música foi modificada desde o último cache.")
            print(f"Cache: {time.ctime(cached_mod_time)}")
            print(f"Atual: {time.ctime(current_mod_time)}")
            return None
        
        # Verifica se os arquivos ainda existem
        songs = cache_data.get("songs", [])
        valid_songs = []
        
        print("Verificando integridade do cache...")
        for song in songs:
            if os.path.exists(song["path"]):
                valid_songs.append(song)
        
        if len(valid_songs) != len(songs):
            print(f"Cache parcialmente inválido: {len(songs) - len(valid_songs)} arquivos removidos.")
            return None
        
        cache_age = time.time() - cache_data.get("timestamp", 0)
        print(f"Cache carregado com sucesso!")
        print(f"Data do cache: {time.ctime(cache_data.get('timestamp', 0))}")
        print(f"Idade do cache: {cache_age / 3600:.1f} horas")
        print(f"Total de músicas: {len(valid_songs)}")
        
        return valid_songs
        
    except Exception as e:
        print(f"Erro ao carregar cache: {e}")
        return None

def list_mp3_files_with_cache(folder, limit=None):
    """Lista arquivos MP3 usando cache quando possível."""
    global use_cache, force_rescan
    
    # Tenta carregar do cache primeiro
    if use_cache and not force_rescan:
        print("Tentando carregar do cache...")
        cached_songs = load_cache(folder)
        if cached_songs:
            if limit:
                cached_songs = cached_songs[:limit]
            return cached_songs
    
    # Se não há cache válido, faz varredura completa
    print("Realizando varredura completa da pasta de música...")
    songs = list_mp3_files(folder, limit)
    
    # Salva no cache para próximas execuções
    if songs and use_cache:
        save_cache(songs, folder)
    
    return songs

# Function to read metadata of an MP3 file
def read_metadata(file_path):
    try:
        metadata = EasyID3(file_path)
        artist = metadata.get("artist", ["Unknown"])[0]
        title = metadata.get("title", ["Untitled"])[0]
        artist = normalize_text(artist)
        return {"path": file_path, "artist": artist, "title": title}
    except Exception as e:
        print(f"Error reading {file_path}: {e}")
        return None

# Function to list MP3 files and extract metadata
def list_mp3_files(folder, limit=None):
    print("Starting to list MP3 files...")
    songs = []
    counter = 0
    current_folder = None

    for root, dirs, files in os.walk(folder):
        if root != current_folder:
            print(f"Processing folder: {root}")
            current_folder = root

        for file in files:
            if file.endswith(".mp3"):
                file_path = os.path.join(root, file)
                song = read_metadata(file_path)
                if song:
                    songs.append(song)
                    counter += 1

                if limit and counter >= limit:
                    print(f"Reached the limit of {limit} files.")
                    return songs

    print(f"Completed listing MP3 files. Total MP3 files found: {len(songs)}")
    return songs

# Function to group songs by "Artist"
def group_by_artist(songs):
    print("Grouping songs by artist...")
    groups = defaultdict(list)
    for song in songs:
        artist = song["artist"]
        groups[artist].append(song)
    print("Completed grouping by artist.")
    return groups

# Function to handle selection logic based on the number of songs per artist
def select_songs_based_on_artist_count(groups_by_artist, songs_per_artist):
    print("Selecting songs based on artist count...")
    selected_songs = []

    # Separate artists into two groups
    group_1 = {artist: songs for artist, songs in groups_by_artist.items() if len(songs) >= 6}
    group_2 = {artist: songs for artist, songs in groups_by_artist.items() if len(songs) <= 5}

    # For Group 1, select `songs_per_artist` songs per artist
    for artist, songs in group_1.items():
        selected_songs.extend(random.sample(songs, songs_per_artist))

    # Calculate 10% of the total songs selected from Group 1
    total_group_1_songs = len(selected_songs)
    group_2_selection_count = max(1, int(total_group_1_songs * 0.1))

    # Randomly select `group_2_selection_count` songs from Group 2 artists
    group_2_songs = [song for songs in group_2.values() for song in songs]
    selected_songs.extend(random.sample(group_2_songs, min(group_2_selection_count, len(group_2_songs))))

    print(f"Total songs selected: {len(selected_songs)} (Group 1: {total_group_1_songs}, Group 2: {group_2_selection_count})")
    return selected_songs

# Function to limit songs based on the maximum size in bytes
def limit_songs_by_size(selected_songs, max_size_bytes):
    print(f"Limiting total size of selected songs to {max_size_gb} GB...")
    limited_songs = []
    current_size = 0

    # Shuffle the selected songs to randomize the order
    random.shuffle(selected_songs)

    for song in selected_songs:
        file_size = os.path.getsize(song["path"])
        if current_size + file_size <= max_size_bytes:
            limited_songs.append(song)
            current_size += file_size
        else:
            break  # Stop adding songs if the limit is reached

    print(f"Total size of limited selection: {current_size / (1024 ** 3):.2f} GB with {len(limited_songs)} songs.")
    return limited_songs

# Helper function to remove special characters from the path
def normalize_path(path):
    return unicodedata.normalize('NFKD', path).encode('ASCII', 'ignore').decode('ASCII')

# Function to copy or create shortcuts (.lnk files) for selected songs
def copy_or_link_selected_songs(selected_songs, destination, copy_mode=True):
    if copy_mode:
        print("Copying selected songs to the destination folder...")
    else:
        print("Creating shortcuts for selected songs in the destination folder...")

    if not os.path.exists(destination):
        os.makedirs(destination)

    for i, song in enumerate(selected_songs, start=1):
        source_path = song["path"]
        file_name = os.path.basename(source_path)
        destination_path = os.path.join(destination, file_name)

        try:
            if copy_mode:
                shutil.copy2(source_path, destination_path)
            else:
                # Normalize path to handle special characters
                source_path_normalized = normalize_path(source_path)
                shell = win32com.client.Dispatch("WScript.Shell")
                shortcut = shell.CreateShortcut(destination_path + ".lnk")
                shortcut.TargetPath = source_path_normalized
                shortcut.Save()

            if i % 10 == 0:
                print(f"{i} songs processed...")
        except Exception as e:
            print(f"Failed to process {file_name}: {e}")

    print("Completed processing songs.")

# Execute the program
print("Starting the song selection program...")
songs = list_mp3_files_with_cache(music_folder, limit=test_limit)

if songs:
    print(f"Total MP3 files found: {len(songs)}")
    groups_by_artist = group_by_artist(songs)
    selected_songs = select_songs_based_on_artist_count(groups_by_artist, songs_per_artist)
    
    # If in copy mode, limit by size; otherwise, proceed without size limitation
    if copy_mode:
        limited_songs = limit_songs_by_size(selected_songs, max_size_bytes)
    else:
        limited_songs = selected_songs  # Ignore size limitation for shortcut creation
    
    if limited_songs:
        copy_or_link_selected_songs(limited_songs, destination_folder, copy_mode=copy_mode)
    else:
        print("No songs selected within the size limit. Exiting program.")
else:
    print("No MP3 files found in the specified folder.")

print("Program completed successfully.")
