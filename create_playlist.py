import os
import win32com.client

# Path to the folder with shortcuts
shortcut_folder = 'C:\\Users\\alexg\\Music\\Temp3'

# Path to the playlist file (M3U)
playlist_path = 'C:\\Users\\alexg\\Music\\Temp3\\playlist.m3u'

# Resolve shortcuts and collect paths
mp3_paths = []
shell = win32com.client.Dispatch("WScript.Shell")

for file in os.listdir(shortcut_folder):
    if file.endswith('.lnk'):
        shortcut_path = os.path.join(shortcut_folder, file)
        resolved_path = shell.CreateShortcut(shortcut_path).Targetpath
        if resolved_path.endswith('.mp3'):
            mp3_paths.append(resolved_path)

# Create the M3U file
with open(playlist_path, 'w', encoding='utf-8') as playlist:
    playlist.write('#EXTM3U\n')
    for path in mp3_paths:
        playlist.write(f'{path}\n')

print(f'Playlist created successfully: {playlist_path}')
