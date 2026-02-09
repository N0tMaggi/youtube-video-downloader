# YouTube Downloader

A simple and easy-to-use YouTube downloader script for downloading audio and video files in various formats.

## Features
- Download YouTube videos in MP3 (high quality), WEBM (original quality), and MP4 (video + audio).
- Option to choose the download format.
- Ability to select the download directory.
- Built-in support for FFmpeg for audio conversion (MP3).
- Interactive user interface.

## Requirements
Before running this script, ensure that the following software is installed on your system:

1. **Python 3.x** - You can download Python from [here](https://www.python.org/downloads/).
2. **FFmpeg** - FFmpeg is required for audio conversion to MP3. You can install FFmpeg from [here](https://ffmpeg.org/download.html).

    Alternatively, you can install FFmpeg via the command:
    ```bash
    winget install ffmpeg
    ```

3. **Required Python packages** - You can install the required packages by running the following command or simply use `install.bat` which installs everything automatically:

    ```bash
    pip install -r requirements.txt
    ```

   **Important:** YouTube frequently changes its player signatures. Always keep `yt-dlp` up to date to avoid `nsig extraction failed` or empty downloads:

    ```bash
    python -m pip install --upgrade yt-dlp
    ```

## Usage
1. Clone this repository or download the script.
2. On Windows, run `install.bat` (requires admin rights) to automatically install dependencies (including FFmpeg) and start the downloader.
   If everything is already installed, you can run the script using Python:

    ```bash
    python downloader.py
    ```

   The script now checks your installed `yt-dlp` version on startup. If it is older than the required version, it will try to upgrade and ask you to restart so downloads stay working.

3. Follow the prompts to select the download format, provide the YouTube URL, and choose a download directory.

4. The script will show a progress spinner during the download and notify you once the download is complete.

## License
This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
