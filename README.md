# MP3 File Selector

A Python tool to organize and manage your MP3 files by creating custom selections based on artists and file size limits.

## Features

### MP3 Selector GUI (`mp3_selector_gui.py`)
- User-friendly graphical interface
- Select source and destination folders through file browser
- Configure all settings through the interface:
  - Maximum songs per artist
  - Total size limit
  - Copy mode (files or shortcuts)
  - **Cache system** for faster subsequent scans
  - **Force rescan** option to bypass cache
- Real-time progress display
- Error handling with user notifications

### MP3 Selector (`mp3_selector.py`)
- Normalizes text and special characters in filenames
- Reads MP3 metadata (ID3 tags)
- Groups songs by artist
- Selects songs based on configurable rules:
  - Maximum number of songs per artist
  - Total size limit in GB
- **Intelligent caching system**:
  - Saves scan results to avoid re-scanning large music libraries
  - Automatically detects when music folder has been modified
  - Validates cache integrity before use
  - Significantly reduces processing time for subsequent runs
- **Parallel processing**:
  - Multi-threaded file scanning and metadata processing
  - Parallel file copying/creation for faster operations
  - Configurable number of worker threads
  - Significant performance improvement for large music libraries
- Supports two output modes:
  - Copy files to destination folder
  - Create shortcuts (.lnk files)

### Playlist Creator (`create_playlist.py`)
- Resolves .lnk shortcuts to find original MP3 files
- Creates .m3u playlist files with correct file paths

## Installation & Usage

### Executable Version (Windows)
The easiest way to use the application is through the executable file:
1. Download the `mp3_selector_gui.exe` from the `dist` folder
2. Double-click to run - no installation or Python required
3. Use the graphical interface to select folders and configure settings

### Python Version
If you prefer to run from source, you'll need Python installed with these requirements:

```bash
pip install mutagen pywin32 tkinter
```

Then you can run either:

### GUI Version (Recommended)
1. Run the GUI version:
```bash
python mp3_selector_gui.py
```
2. Use the interface to:
   - Select folders
   - Configure settings
   - Start the selection process

### Command Line Version
1. Set up your configuration in the script
2. Run the MP3 selector:
```bash
python mp3_selector.py
```
3. To create a playlist from the selected files:
```bash
python create_playlist.py
```

## Configuration

### GUI Version (Recommended)
All configuration is done through the graphical interface:
- **Source Folder**: Select your music library folder
- **Destination Folder**: Choose where to save selected songs
- **File Limit**: Maximum number of files to process (999999 = no limit)
- **Songs per Artist**: Maximum songs to select per artist
- **Max Size (GB)**: Total size limit for selected songs
- **Mode**: Choose between copying files or creating shortcuts
- **Use Cache**: Enable/disable the caching system
- **Force Rescan**: Bypass cache and perform full scan
- **Parallel Workers**: Number of threads for parallel processing (default: 4)

### Command Line Version
Edit the following variables in the scripts to customize behavior:

```python
# in mp3_selector.py
music_folder = r"D:\Music"                    # Source music folder
destination_folder = r"C:\Users\alexg\Music\Temp3"  # Output folder
# cache_folder is automatically set to project_root/cache/
test_limit = 999999                           # File processing limit
songs_per_artist = 3                          # Songs per artist
max_size_gb = 7                              # Size limit in GB
copy_mode = True                             # True=copy, False=shortcuts
use_cache = True                             # Enable caching system
force_rescan = False                         # Force full rescan
parallel_workers = 4                         # Number of parallel threads
```

## How it Works

1. **Smart Scanning**: The script first checks for a valid cache file
   - If cache exists and is valid, loads the previous scan results instantly
   - If no cache or cache is outdated, performs a full folder scan
   - Cache is automatically saved after each successful scan
2. **Metadata Processing**: Reads MP3 metadata to group songs by artist
3. **Intelligent Selection**: Randomly selects songs while respecting the configured limits
4. **Output Generation**: Either copies files or creates shortcuts in the destination folder
5. **Playlist Creation**: Optionally creates a playlist file with the selected songs

### Cache System Benefits

- **First Run**: Full scan of your music library (may take several minutes for large collections)
- **Subsequent Runs**: Near-instant loading from cache (seconds instead of minutes)
- **Automatic Updates**: Cache is automatically invalidated when music folder is modified
- **Data Integrity**: Validates that all cached files still exist before using cache
- **Storage Efficient**: Cache files are small JSON files containing only metadata
- **Organized Storage**: Cache files are stored in `cache/` folder within the project directory

## Contributing

Feel free to open issues or submit pull requests with improvements.

## License

This project is licensed under the MIT License - see the LICENSE file for details.
