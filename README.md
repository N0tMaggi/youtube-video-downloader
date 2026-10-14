# YouTube Downloader

A modern and easy-to-use YouTube downloader script featuring an interactive Terminal User Interface (TUI) powered by `rich` and `questionary`.

## Features
- **Modern Interactive TUI**: Smooth arrow-key navigation, styled banners, video detail cards, and live download progress bars (with speed, percentage, ETA, and size).
- **Browser Cookies & Bot-Check Bypass**: Easily load session cookies from installed browsers (Firefox, Brave, Chrome, Edge, Opera, Opera GX, Vivaldi) to bypass "Sign in to confirm you're not a bot" checks.
- **Node.js JS Runtime Support**: Automatic challenge solving for YouTube rolling player signatures.
- **Multiple Formats**: Download YouTube videos in MP4 (best video + audio), MP3 (192kbps high quality via FFmpeg), or original WEBM audio/video.
- **Configurable Settings**: Change and save your default download directory and preferred browser in `config.json`.
- **Post-Download Actions**: Open the containing folder in File Explorer or immediately play the downloaded file.

## Requirements
Before running this script, ensure the following software is installed on your system:

1. **Python 3.x** - [Download Python](https://www.python.org/downloads/)
2. **FFmpeg** - Required for MP3 audio conversion:
   ```bash
   winget install ffmpeg
   ```
3. **Node.js** *(Recommended)* - Required by `yt-dlp` for solving JavaScript signature challenges:
   ```bash
   winget install OpenJS.NodeJS
   ```
4. **Python packages**:
   ```bash
   pip install -r requirements.txt
   ```

## Usage
1. Clone or download this repository.
2. Double-click `run.bat` or run:
   ```bash
   python downloader.py
   ```
3. Use the arrow keys to navigate the menu:
   - **Download Video**: Enter any YouTube URL, select format, and download.
   - **Select Cookie Browser**: Choose your browser to authenticate with YouTube.
   - **Change Download Directory**: Customize where downloaded files are saved.

## License
This project is licensed under the MIT License - see the [LICENSE.txt](LICENSE.txt) file for details.
