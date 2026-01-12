import os
import shutil
import threading
import json
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from tkinter import Tk, Label, Entry, Button, StringVar, IntVar, filedialog, messagebox, Radiobutton, Frame, ttk, Checkbutton
from mutagen.easyid3 import EasyID3
from collections import defaultdict

# Variável global para controlar a interrupção do processo
stop_flag = False

# Cache management functions
def get_cache_filename(music_folder):
    """Gera nome único do arquivo de cache baseado na pasta de música."""
    # Pasta cache na raiz do projeto
    cache_folder = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cache")
    folder_hash = abs(hash(music_folder)) % (10 ** 8)
    return os.path.join(cache_folder, f"music_cache_{folder_hash}.json")

def get_folder_modification_time(folder):
    """Obtém o tempo de modificação mais recente da pasta e subpastas."""
    try:
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
    except Exception as e:
        print(f"Erro ao obter tempo de modificação: {e}")
        return 0

def save_cache(songs, music_folder):
    """Salva a lista de músicas no cache."""
    try:
        print(f"=== DEBUG SAVE_CACHE ===")
        print(f"music_folder: {music_folder}")
        print(f"len(songs): {len(songs)}")
        
        # Pasta cache na raiz do projeto
        cache_folder = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cache")
        print(f"cache_folder: {cache_folder}")
        
        if not os.path.exists(cache_folder):
            print("Creating cache folder...")
            os.makedirs(cache_folder)
            print("Cache folder created!")
        else:
            print("Cache folder already exists!")
        
        cache_data = {
            "timestamp": time.time(),
            "music_folder": music_folder,
            "folder_mod_time": get_folder_modification_time(music_folder),
            "songs": songs,
            "total_songs": len(songs)
        }
        
        cache_file = get_cache_filename(music_folder)
        print(f"cache_file: {cache_file}")
        
        print("Writing cache file...")
        with open(cache_file, 'w', encoding='utf-8') as f:
            json.dump(cache_data, f, ensure_ascii=False, indent=2)
        
        print(f"✅ Cache salvo com sucesso: {cache_file}")
        print(f"Total de músicas em cache: {len(songs)}")
        
        # Verify if file was actually created
        if os.path.exists(cache_file):
            file_size = os.path.getsize(cache_file)
            print(f"File created successfully! Size: {file_size} bytes")
        else:
            print("❌ ERROR: File was not created!")
        
        return True
    except Exception as e:
        print(f"❌ Erro ao salvar cache: {e}")
        import traceback
        traceback.print_exc()
        return False

def load_cache(music_folder, manual_path=None):
    """Loads the music list from cache if available and valid."""
    try:
        if manual_path and os.path.exists(manual_path):
            cache_file = manual_path
            print(f"Using manual cache file: {cache_file}")
        else:
            cache_file = get_cache_filename(music_folder)
        
        if not os.path.exists(cache_file):
            print("Cache file not found.")
            return None
        
        with open(cache_file, 'r', encoding='utf-8') as f:
            cache_data = json.load(f)
        
        # Se NÃO for manual, faz as validações automáticas de pasta e tempo
        if not manual_path:
            # Verify if cache is for the same folder
            if cache_data.get("music_folder") != music_folder:
                print("Cache is for a different folder.")
                return None
            
            # Verify if folder was modified since cache
            current_mod_time = get_folder_modification_time(music_folder)
            cached_mod_time = cache_data.get("folder_mod_time", 0)
            
            if current_mod_time > cached_mod_time:
                print("Music folder has been modified since last cache.")
                print(f"Cache: {time.ctime(cached_mod_time)}")
                print(f"Current: {time.ctime(current_mod_time)}")
                return None
        
        # Verify if files still exist
        songs = cache_data.get("songs", [])
        valid_songs = []
        
        print("Checking cache integrity...")
        for song in songs:
            if os.path.exists(song["path"]):
                valid_songs.append(song)
        
        if len(valid_songs) != len(songs):
            print(f"Cache partially invalid: {len(songs) - len(valid_songs)} files removed.")
            if not manual_path: # If automatic, invalidate. If manual, use what's left.
                return None
        
        cache_age = time.time() - cache_data.get("timestamp", 0)
        print(f"Cache loaded successfully!")
        print(f"Cache date: {time.ctime(cache_data.get('timestamp', 0))}")
        print(f"Cache age: {cache_age / 3600:.1f} hours")
        print(f"Total songs: {len(valid_songs)}")
        
        return valid_songs
        
    except Exception as e:
        print(f"Error loading cache: {e}")
        return None

def count_folders_and_files(folder_path):
    """Conta o número total de pastas e arquivos em uma pasta especificada."""
    total_folders = 0
    total_files = 0
    for _, dirs, files in os.walk(folder_path):
        total_folders += len(dirs)
        total_files += len(files)
    return total_folders, total_files

def list_mp3_files(folder_path, progress_var, status_label, root, limit=None):
    """Lista todos os arquivos MP3 em uma pasta especificada."""
    global stop_flag
    print(f"Listando arquivos MP3 na pasta: {folder_path}")
    mp3_files = []
    total_folders, total_files = count_folders_and_files(folder_path)
    processed_folders = 0
    processed_files = 0

    for root_dir, _, files in os.walk(folder_path):
        if stop_flag:
            break
        for file in files:
            if stop_flag:
                break
            if file.lower().endswith('.mp3'):
                mp3_files.append(os.path.join(root_dir, file))
            processed_files += 1
            progress_var.set((processed_files / total_files) * 100)
            status_label.config(text=f"Scanning files... ({processed_files}/{total_files})")
            root.update_idletasks()  # Forces update of the GUI
        processed_folders += 1
        status_label.config(text=f"Scanning folders... ({processed_folders}/{total_folders})")
        root.update_idletasks()  # Forces update of the GUI

    if limit:
        mp3_files = mp3_files[:limit]
    print(f"Número de arquivos MP3 encontrados: {len(mp3_files)}")
    return mp3_files

def list_mp3_files_parallel(folder_path, progress_var, status_label, root, limit=None, max_workers=20):
    """Lista todos os arquivos MP3 em uma pasta especificada usando paralelização."""
    global stop_flag
    print(f"Listing MP3 files in folder (PARALLEL): {folder_path}")
    
    # Phase 1: Collecting MP3 files
    mp3_files = []
    processed_files = 0
    print("Phase 1: Collecting MP3 files...")
    
    # Combined walk to avoid double scanning disk
    for root_dir, _, files in os.walk(folder_path):
        if stop_flag:
            break
        for file in files:
            if stop_flag:
                break
            if file.lower().endswith('.mp3'):
                mp3_files.append(os.path.join(root_dir, file))
            
            processed_files += 1
            # Update UI only every 1000 files to avoid overhead
            if processed_files % 1000 == 0:
                status_label.config(text=f"Searching... {len(mp3_files)} MP3s found ({processed_files} total files)")
                root.update_idletasks()

    if stop_flag:
        return []

    if limit:
        mp3_files = mp3_files[:limit]
    
    print(f"MP3 files found: {len(mp3_files)}")
    
    if not mp3_files:
        return mp3_files

    # Phase 2: Parallel processing of metadata
    print("Phase 2: Processing metadata in parallel...")
    songs_with_metadata = []
    completed = 0
    
    def process_single_file(file_path):
        """Processa um único arquivo MP3 e retorna seus metadados."""
        if stop_flag:
            return None
        try:
            audio = EasyID3(file_path)
            artist = audio.get('artist', ['Unknown'])[0]
            title = audio.get('title', ['Untitled'])[0]
            return {
                "path": file_path,
                "artist": artist.lower(),
                "title": title
            }
        except Exception as e:
            print(f"Erro ao processar {file_path}: {e}")
            return {
                "path": file_path,
                "artist": "unknown",
                "title": "untitled"
            }
    
    # Usar ThreadPoolExecutor para processamento paralelo
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # Submeter todas as tarefas
        future_to_file = {executor.submit(process_single_file, file_path): file_path 
                         for file_path in mp3_files}
        
        # Processar resultados conforme completam
        for future in as_completed(future_to_file):
            if stop_flag:
                break
                
            result = future.result()
            if result:
                songs_with_metadata.append(result)
            
            completed += 1
            # Optimization: Update UI only every 100 files in Phase 2
            if completed % 100 == 0 or completed == len(mp3_files):
                progress = 50 + (completed / len(mp3_files)) * 50
                progress_var.set(progress)
                status_label.config(text=f"Processing metadata... ({completed}/{len(mp3_files)})")
                root.update_idletasks()
    
    print(f"Parallel processing complete: {len(songs_with_metadata)} files processed")
    return songs_with_metadata

def list_mp3_files_with_cache(folder_path, progress_var, status_label, root, limit=None):
    """Lista arquivos MP3 usando cache quando possível."""
    global stop_flag
    
    print(f"=== DEBUG CACHE ===")
    print(f"use_cache.get(): {use_cache.get()}")
    print(f"force_rescan.get(): {force_rescan.get()}")
    print(f"folder_path: {folder_path}")
    
    # Tenta carregar do cache primeiro
    if use_cache.get() and not force_rescan.get():
        print("Attempting to load from cache...")
        status_label.config(text="Attempting to load from cache...")
        root.update_idletasks()
        
        manual_path = manual_cache_path.get()
        cached_songs = load_cache(folder_path, manual_path=manual_path if manual_path else None)
        if cached_songs:
            print(f"Cache carregado com sucesso: {len(cached_songs)} músicas")
            # Converte para formato esperado (lista de paths)
            mp3_files = [song["path"] for song in cached_songs]
            if limit:
                mp3_files = mp3_files[:limit]
            progress_var.set(100)
            status_label.config(text=f"Cache loaded: {len(mp3_files)} files")
            root.update_idletasks()
            return mp3_files
        else:
            print("Cache not found or invalid, performing full scan...")
    else:
        print("Cache disabled or forcing rescan, performing full scan...")
    
    # If no valid cache, perform full scan
    status_label.config(text="Performing full scan...")
    root.update_idletasks()
    # Now it returns the full objects with metadata
    songs_with_metadata = list_mp3_files_parallel(folder_path, progress_var, status_label, root, limit)
    
    # Saves to cache for next runs (now it's instant because we already have the metadata!)
    if songs_with_metadata and (use_cache.get() or only_cache.get()):
        print(f"Saving {len(songs_with_metadata)} songs to cache...")
        save_cache(songs_with_metadata, folder_path)
    else:
        print("Cache disabled or no songs found, not saving cache.")
    
    # Returns only paths to maintain compatibility with the rest of the script
    return [song["path"] for song in songs_with_metadata]

def group_by_artist(mp3_files):
    """Groups MP3 files by artist."""
    print("Grouping MP3 files by artist...")
    groups = defaultdict(list)
    for file in mp3_files:
        if stop_flag:
            break
        try:
            audio = EasyID3(file)
            artist = audio['artist'][0]
            groups[artist].append(file)
        except Exception as e:
            print(f"Error reading metadata from file {file}: {e}")
    print(f"Number of artists found: {len(groups)}")
    return groups

def select_songs_based_on_artist_count(groups_by_artist, songs_per_artist):
    """Selects a specific number of songs per artist."""
    print(f"Selecting up to {songs_per_artist} songs per artist...")
    selected_songs = []
    for artist, songs in groups_by_artist.items():
        if stop_flag:
            break
        selected_songs.extend(songs[:songs_per_artist])
    print(f"Number of songs selected: {len(selected_songs)}")
    return selected_songs

def limit_songs_by_size(selected_songs, max_size_bytes):
    """Limits the selection of songs based on total size."""
    print(f"Limiting selected songs to a total of {max_size_bytes} bytes...")
    total_size = 0
    limited_songs = []
    for song in selected_songs:
        if stop_flag:
            break
        song_size = os.path.getsize(song)
        if total_size + song_size <= max_size_bytes:
            limited_songs.append(song)
            total_size += song_size
        else:
            break
    print(f"Number of songs after size limitation: {len(limited_songs)}")
    return limited_songs

def copy_or_link_selected_songs(songs, destination_folder, progress_var, status_label, root, copy_mode=True):
    """Copia ou cria atalhos para as músicas selecionadas na pasta de destino."""
    global stop_flag
    print(f"{'Copiando' if copy_mode else 'Criando atalhos para'} músicas na pasta de destino: {destination_folder}")
    if not os.path.exists(destination_folder):
        os.makedirs(destination_folder)
    total_songs = len(songs)
    for i, song in enumerate(songs):
        if stop_flag:
            break
        destination_path = os.path.join(destination_folder, os.path.basename(song))
        if copy_mode:
            shutil.copy2(song, destination_path)
        else:
            os.symlink(song, destination_path)
        progress_var.set((i + 1) / total_songs * 100)
        status_label.config(text=f"Processing {i + 1} of {total_songs} songs...")
        root.update_idletasks()  # Forces update of the GUI
    print("Copy/link process completed.")
    status_label.config(text="Process completed.")

# Funções auxiliares para a interface gráfica
def select_music_folder():
    folder_selected = filedialog.askdirectory()
    music_folder.set(folder_selected)

def select_destination_folder():
    folder_selected = filedialog.askdirectory()
    destination_folder.set(folder_selected)

def select_manual_cache_file():
    file_selected = filedialog.askopenfilename(filetypes=[("JSON files", "*.json"), ("All files", "*.*")])
    if file_selected:
        manual_cache_path.set(file_selected)
        use_cache.set(1) # Ativa o uso de cache automaticamente ao selecionar um arquivo

def start_process(root):
    global stop_flag
    stop_flag = False
    print("Iniciando o processo...")
    try:
        music_folder_path = music_folder.get()
        destination_folder_path = destination_folder.get()
        test_limit_value = test_limit.get()
        songs_per_artist_value = songs_per_artist.get()
        max_size_gb_value = max_size_gb.get()
        copy_mode_value = copy_mode.get() == 1

        print(f"Music folder: {music_folder_path}")
        print(f"Destination folder: {destination_folder_path}")
        print(f"File limit: {test_limit_value}")
        print(f"Songs per artist: {songs_per_artist_value}")
        print(f"Max size (GB): {max_size_gb_value}")
        print(f"Copy mode: {'Copy' if copy_mode_value else 'Create Shortcuts'}")

        # Step 1: Scanning MP3 files
        status_label.config(text="Starting MP3 file scan...")
        root.update_idletasks()
        songs = list_mp3_files_with_cache(music_folder_path, progress_var, status_label, root, limit=test_limit_value)
        print(f"Number of songs found: {len(songs)}")
        overall_progress_var.set(33)  # Update overall progress to 33%
        root.update_idletasks()

        if stop_flag:
            raise Exception("Process interrupted by user.")

        if only_cache.get() == 1:
            if songs:
                overall_progress_var.set(100)
                messagebox.showinfo("Success", f"Scanning complete! Cache created/updated with {len(songs)} songs.")
                return
            else:
                messagebox.showwarning("Warning", "No MP3 files found to cache.")
                return

        if songs:
            # Step 2: Grouping and selecting songs
            status_label.config(text="Grouping and selecting songs...")
            root.update_idletasks()
            groups_by_artist = group_by_artist(songs)
            selected_songs = select_songs_based_on_artist_count(groups_by_artist, songs_per_artist_value)
            if copy_mode_value:
                limited_songs = limit_songs_by_size(selected_songs, max_size_gb_value * (1024 ** 3))
            else:
                limited_songs = selected_songs
            overall_progress_var.set(66)  # Update overall progress to 66%
            root.update_idletasks()

            if stop_flag:
                raise Exception("Process interrupted by user.")

            if limited_songs:
                # Step 3: Copying or creating shortcuts for selected files
                status_label.config(text="Copying or creating shortcuts for selected songs...")
                root.update_idletasks()
                copy_or_link_selected_songs(limited_songs, destination_folder_path, progress_var, status_label, root, copy_mode=copy_mode_value)
                overall_progress_var.set(100)  # Update overall progress to 100%
                root.update_idletasks()
                if stop_flag:
                    raise Exception("Process interrupted by user.")
                messagebox.showinfo("Success", "Process completed successfully!")
            else:
                messagebox.showwarning("Warning", "No songs selected within the size limit.")
        else:
            messagebox.showwarning("Warning", "No MP3 files found in the specified folder.")
    except Exception as e:
        print(f"Error: {e}")
        messagebox.showerror("Error", f"An error occurred: {e}")
    finally:
        start_button.config(state='normal')
        stop_button.config(state='disabled')
        status_label.config(text="")

def start_process_thread():
    print("Starting thread...")
    status_label.config(text="Starting process...")
    start_button.config(state='disabled')
    stop_button.config(state='normal')
    process_thread = threading.Thread(target=start_process, args=(root,))
    process_thread.start()
    print("Thread started.")

def stop_process():
    global stop_flag
    stop_flag = True
    print("Process interrupted by user.")
    status_label.config(text="Process interrupted by user.")
    root.update_idletasks()

# GUI Creation
root = Tk()
root.title("MP3 Music Selector")
root.geometry("600x530")
root.configure(bg="#f0f4f7")

# Variáveis para armazenar os valores dos campos de entrada
music_folder = StringVar()
destination_folder = StringVar()
test_limit = IntVar(value=999999)
songs_per_artist = IntVar(value=3)
max_size_gb = IntVar(value=10)
copy_mode = IntVar(value=1)
use_cache = IntVar(value=1)  # Usar cache por padrão
force_rescan = IntVar(value=0)  # Não forçar rescan por padrão
only_cache = IntVar(value=0)    # Only create cache
manual_cache_path = StringVar()
parallel_workers = IntVar(value=10)  # Increased default thread count
progress_var = IntVar(value=0)
overall_progress_var = IntVar(value=0)

# Layout da interface gráfica
frame = Frame(root, padx=10, pady=10, bg="#f0f4f7")
frame.pack(fill='both', expand=True)

Label(frame, text="Music Folder:", bg="#f0f4f7").grid(row=0, column=0, sticky='e')
Entry(frame, textvariable=music_folder, width=50).grid(row=0, column=1)
Button(frame, text="Select", command=select_music_folder, bg="#d9e4f5", activebackground="#c3d3ef").grid(row=0, column=2)

Label(frame, text="Destination Folder:", bg="#f0f4f7").grid(row=1, column=0, sticky='e')
Entry(frame, textvariable=destination_folder, width=50).grid(row=1, column=1)
Button(frame, text="Select", command=select_destination_folder, bg="#d9e4f5", activebackground="#c3d3ef").grid(row=1, column=2)

Label(frame, text="File Limit:", bg="#f0f4f7").grid(row=2, column=0, sticky='e')
Entry(frame, textvariable=test_limit).grid(row=2, column=1)

Label(frame, text="Songs per Artist:", bg="#f0f4f7").grid(row=3, column=0, sticky='e')
Entry(frame, textvariable=songs_per_artist).grid(row=3, column=1)

Label(frame, text="Max Size (GB):", bg="#f0f4f7").grid(row=4, column=0, sticky='e')
Entry(frame, textvariable=max_size_gb).grid(row=4, column=1)

Label(frame, text="Mode:", bg="#f0f4f7").grid(row=5, column=0, sticky='e')
Radiobutton(frame, text="Copy", variable=copy_mode, value=1, bg="#f0f4f7").grid(row=5, column=1, sticky='w')
Radiobutton(frame, text="Create Shortcuts", variable=copy_mode, value=0, bg="#f0f4f7").grid(row=5, column=1, sticky='e')

# Cache controls
Label(frame, text="Cache:", bg="#f0f4f7").grid(row=6, column=0, sticky='e')
Checkbutton(frame, text="Use Cache", variable=use_cache, bg="#f0f4f7").grid(row=6, column=1, sticky='w')
Checkbutton(frame, text="Force Rescan", variable=force_rescan, bg="#f0f4f7").grid(row=6, column=2, sticky='w')
Checkbutton(frame, text="Only Create Cache", variable=only_cache, bg="#f0f4f7").grid(row=6, column=1, sticky='e')

Label(frame, text="Manual Cache:", bg="#f0f4f7").grid(row=7, column=0, sticky='e')
Entry(frame, textvariable=manual_cache_path, width=50).grid(row=7, column=1)
Button(frame, text="Browse", command=select_manual_cache_file, bg="#d9e4f5", activebackground="#c3d3ef").grid(row=7, column=2)

start_button = Button(frame, text="Start", command=start_process_thread, bg="#b5d1f0", activebackground="#a4c4e8")
start_button.grid(row=8, column=0, columnspan=2, pady=10)

stop_button = Button(frame, text="Stop", command=stop_process, bg="#f0b5b5", activebackground="#f0a4a4", state='disabled')
stop_button.grid(row=8, column=2, pady=10)

progress = ttk.Progressbar(frame, orient="horizontal", length=400, mode="determinate", variable=progress_var)
progress.grid(row=9, column=0, columnspan=3, pady=10)

overall_progress = ttk.Progressbar(frame, orient="horizontal", length=400, mode="determinate", variable=overall_progress_var)
overall_progress.grid(row=10, column=0, columnspan=3, pady=10)

status_label = Label(frame, text="", bg="#f0f4f7")
status_label.grid(row=11, column=0, columnspan=3)

root.mainloop()
