import os
import shutil
import threading
import json
import time
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
            print("Criando pasta cache...")
            os.makedirs(cache_folder)
            print("Pasta cache criada!")
        else:
            print("Pasta cache já existe!")
        
        cache_data = {
            "timestamp": time.time(),
            "music_folder": music_folder,
            "folder_mod_time": get_folder_modification_time(music_folder),
            "songs": songs,
            "total_songs": len(songs)
        }
        
        cache_file = get_cache_filename(music_folder)
        print(f"cache_file: {cache_file}")
        
        print("Escrevendo arquivo de cache...")
        with open(cache_file, 'w', encoding='utf-8') as f:
            json.dump(cache_data, f, ensure_ascii=False, indent=2)
        
        print(f"✅ Cache salvo com sucesso: {cache_file}")
        print(f"Total de músicas em cache: {len(songs)}")
        
        # Verificar se o arquivo foi realmente criado
        if os.path.exists(cache_file):
            file_size = os.path.getsize(cache_file)
            print(f"Arquivo criado com sucesso! Tamanho: {file_size} bytes")
        else:
            print("❌ ERRO: Arquivo não foi criado!")
        
        return True
    except Exception as e:
        print(f"❌ Erro ao salvar cache: {e}")
        import traceback
        traceback.print_exc()
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
            status_label.config(text=f"Escaneando arquivos... ({processed_files}/{total_files})")
            root.update_idletasks()  # Força a atualização da interface gráfica
        processed_folders += 1
        status_label.config(text=f"Escaneando pastas... ({processed_folders}/{total_folders})")
        root.update_idletasks()  # Força a atualização da interface gráfica

    if limit:
        mp3_files = mp3_files[:limit]
    print(f"Número de arquivos MP3 encontrados: {len(mp3_files)}")
    return mp3_files

def list_mp3_files_with_cache(folder_path, progress_var, status_label, root, limit=None):
    """Lista arquivos MP3 usando cache quando possível."""
    global stop_flag
    
    print(f"=== DEBUG CACHE ===")
    print(f"use_cache.get(): {use_cache.get()}")
    print(f"force_rescan.get(): {force_rescan.get()}")
    print(f"folder_path: {folder_path}")
    
    # Tenta carregar do cache primeiro
    if use_cache.get() and not force_rescan.get():
        print("Tentando carregar do cache...")
        status_label.config(text="Tentando carregar do cache...")
        root.update_idletasks()
        cached_songs = load_cache(folder_path)
        if cached_songs:
            print(f"Cache carregado com sucesso: {len(cached_songs)} músicas")
            # Converte para formato esperado (lista de paths)
            mp3_files = [song["path"] for song in cached_songs]
            if limit:
                mp3_files = mp3_files[:limit]
            progress_var.set(100)
            status_label.config(text=f"Cache carregado: {len(mp3_files)} arquivos")
            root.update_idletasks()
            return mp3_files
        else:
            print("Cache não encontrado ou inválido, fazendo varredura completa...")
    else:
        print("Cache desabilitado ou forçando rescan, fazendo varredura completa...")
    
    # Se não há cache válido, faz varredura completa
    status_label.config(text="Realizando varredura completa...")
    root.update_idletasks()
    mp3_files = list_mp3_files(folder_path, progress_var, status_label, root, limit)
    
    # Salva no cache para próximas execuções
    if mp3_files and use_cache.get():
        print(f"Salvando {len(mp3_files)} músicas no cache...")
        # Converte para formato de cache (lista de dicionários com metadados)
        songs_with_metadata = []
        for file_path in mp3_files:
            try:
                audio = EasyID3(file_path)
                artist = audio.get('artist', ['Unknown'])[0]
                title = audio.get('title', ['Untitled'])[0]
                songs_with_metadata.append({
                    "path": file_path,
                    "artist": artist.lower(),
                    "title": title
                })
            except:
                songs_with_metadata.append({
                    "path": file_path,
                    "artist": "unknown",
                    "title": "untitled"
                })
        
        save_cache(songs_with_metadata, folder_path)
    else:
        print("Cache desabilitado ou nenhuma música encontrada, não salvando cache.")
    
    return mp3_files

def group_by_artist(mp3_files):
    """Agrupa os arquivos MP3 por artista."""
    print("Agrupando arquivos MP3 por artista...")
    groups = defaultdict(list)
    for file in mp3_files:
        if stop_flag:
            break
        try:
            audio = EasyID3(file)
            artist = audio['artist'][0]
            groups[artist].append(file)
        except Exception as e:
            print(f"Erro ao ler metadados do arquivo {file}: {e}")
    print(f"Número de artistas encontrados: {len(groups)}")
    return groups

def select_songs_based_on_artist_count(groups_by_artist, songs_per_artist):
    """Seleciona um número específico de músicas por artista."""
    print(f"Selecionando até {songs_per_artist} músicas por artista...")
    selected_songs = []
    for artist, songs in groups_by_artist.items():
        if stop_flag:
            break
        selected_songs.extend(songs[:songs_per_artist])
    print(f"Número de músicas selecionadas: {len(selected_songs)}")
    return selected_songs

def limit_songs_by_size(selected_songs, max_size_bytes):
    """Limita a seleção de músicas com base no tamanho total."""
    print(f"Limitando músicas selecionadas para um total de {max_size_bytes} bytes...")
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
    print(f"Número de músicas após limitação por tamanho: {len(limited_songs)}")
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
        status_label.config(text=f"Processando {i + 1} de {total_songs} músicas...")
        root.update_idletasks()  # Força a atualização da interface gráfica
    print("Processo de cópia/conexão concluído.")
    status_label.config(text="Processo concluído.")

# Funções auxiliares para a interface gráfica
def select_music_folder():
    folder_selected = filedialog.askdirectory()
    music_folder.set(folder_selected)

def select_destination_folder():
    folder_selected = filedialog.askdirectory()
    destination_folder.set(folder_selected)

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

        print(f"Pasta de músicas: {music_folder_path}")
        print(f"Pasta de destino: {destination_folder_path}")
        print(f"Limite de arquivos: {test_limit_value}")
        print(f"Músicas por artista: {songs_per_artist_value}")
        print(f"Tamanho máximo (GB): {max_size_gb_value}")
        print(f"Modo de cópia: {'Copiar' if copy_mode_value else 'Criar Atalhos'}")

        # Etapa 1: Escaneamento dos arquivos MP3
        status_label.config(text="Iniciando escaneamento dos arquivos MP3...")
        root.update_idletasks()
        songs = list_mp3_files_with_cache(music_folder_path, progress_var, status_label, root, limit=test_limit_value)
        print(f"Número de músicas encontradas: {len(songs)}")
        overall_progress_var.set(33)  # Atualiza o progresso geral para 33%
        root.update_idletasks()

        if stop_flag:
            raise Exception("Processo interrompido pelo usuário.")

        if songs:
            # Etapa 2: Agrupamento e seleção de músicas
            status_label.config(text="Agrupando e selecionando músicas...")
            root.update_idletasks()
            groups_by_artist = group_by_artist(songs)
            selected_songs = select_songs_based_on_artist_count(groups_by_artist, songs_per_artist_value)
            if copy_mode_value:
                limited_songs = limit_songs_by_size(selected_songs, max_size_gb_value * (1024 ** 3))
            else:
                limited_songs = selected_songs
            overall_progress_var.set(66)  # Atualiza o progresso geral para 66%
            root.update_idletasks()

            if stop_flag:
                raise Exception("Processo interrompido pelo usuário.")

            if limited_songs:
                # Etapa 3: Cópia ou criação de atalhos dos arquivos selecionados
                status_label.config(text="Copiando ou criando atalhos das músicas selecionadas...")
                root.update_idletasks()
                copy_or_link_selected_songs(limited_songs, destination_folder_path, progress_var, status_label, root, copy_mode=copy_mode_value)
                overall_progress_var.set(100)  # Atualiza o progresso geral para 100%
                root.update_idletasks()
                if stop_flag:
                    raise Exception("Processo interrompido pelo usuário.")
                messagebox.showinfo("Sucesso", "Processo concluído com sucesso!")
            else:
                messagebox.showwarning("Aviso", "Nenhuma música selecionada dentro do limite de tamanho.")
        else:
            messagebox.showwarning("Aviso", "Nenhum arquivo MP3 encontrado na pasta especificada.")
    except Exception as e:
        print(f"Erro: {e}")
        messagebox.showerror("Erro", f"Ocorreu um erro: {e}")
    finally:
        start_button.config(state='normal')
        stop_button.config(state='disabled')
        status_label.config(text="")

def start_process_thread():
    print("Iniciando a thread...")
    status_label.config(text="Iniciando o processo...")
    start_button.config(state='disabled')
    stop_button.config(state='normal')
    process_thread = threading.Thread(target=start_process, args=(root,))
    process_thread.start()
    print("Thread iniciada.")

def stop_process():
    global stop_flag
    stop_flag = True
    print("Processo interrompido pelo usuário.")
    status_label.config(text="Processo interrompido pelo usuário.")
    root.update_idletasks()

# Criação da interface gráfica
root = Tk()
root.title("Seleção de Músicas MP3")
root.geometry("600x500")
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
progress_var = IntVar(value=0)
overall_progress_var = IntVar(value=0)

# Layout da interface gráfica
frame = Frame(root, padx=10, pady=10, bg="#f0f4f7")
frame.pack(fill='both', expand=True)

Label(frame, text="Pasta de Músicas:", bg="#f0f4f7").grid(row=0, column=0, sticky='e')
Entry(frame, textvariable=music_folder, width=50).grid(row=0, column=1)
Button(frame, text="Selecionar", command=select_music_folder, bg="#d9e4f5", activebackground="#c3d3ef").grid(row=0, column=2)

Label(frame, text="Pasta de Destino:", bg="#f0f4f7").grid(row=1, column=0, sticky='e')
Entry(frame, textvariable=destination_folder, width=50).grid(row=1, column=1)
Button(frame, text="Selecionar", command=select_destination_folder, bg="#d9e4f5", activebackground="#c3d3ef").grid(row=1, column=2)

Label(frame, text="Limite de Arquivos:", bg="#f0f4f7").grid(row=2, column=0, sticky='e')
Entry(frame, textvariable=test_limit).grid(row=2, column=1)

Label(frame, text="Músicas por Artista:", bg="#f0f4f7").grid(row=3, column=0, sticky='e')
Entry(frame, textvariable=songs_per_artist).grid(row=3, column=1)

Label(frame, text="Tamanho Máximo (GB):", bg="#f0f4f7").grid(row=4, column=0, sticky='e')
Entry(frame, textvariable=max_size_gb).grid(row=4, column=1)

Label(frame, text="Modo:", bg="#f0f4f7").grid(row=5, column=0, sticky='e')
Radiobutton(frame, text="Copiar", variable=copy_mode, value=1, bg="#f0f4f7").grid(row=5, column=1, sticky='w')
Radiobutton(frame, text="Criar Atalhos", variable=copy_mode, value=0, bg="#f0f4f7").grid(row=5, column=1, sticky='e')

# Controles de cache
Label(frame, text="Cache:", bg="#f0f4f7").grid(row=6, column=0, sticky='e')
Checkbutton(frame, text="Usar Cache", variable=use_cache, bg="#f0f4f7").grid(row=6, column=1, sticky='w')
Checkbutton(frame, text="Forçar Rescan", variable=force_rescan, bg="#f0f4f7").grid(row=6, column=2, sticky='w')

start_button = Button(frame, text="Iniciar", command=start_process_thread, bg="#b5d1f0", activebackground="#a4c4e8")
start_button.grid(row=7, column=0, columnspan=2, pady=10)

stop_button = Button(frame, text="Parar", command=stop_process, bg="#f0b5b5", activebackground="#f0a4a4", state='disabled')
stop_button.grid(row=7, column=2, pady=10)

progress = ttk.Progressbar(frame, orient="horizontal", length=400, mode="determinate", variable=progress_var)
progress.grid(row=8, column=0, columnspan=3, pady=10)

overall_progress = ttk.Progressbar(frame, orient="horizontal", length=400, mode="determinate", variable=overall_progress_var)
overall_progress.grid(row=9, column=0, columnspan=3, pady=10)

status_label = Label(frame, text="", bg="#f0f4f7")
status_label.grid(row=10, column=0, columnspan=3)

root.mainloop()
