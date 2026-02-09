import yt_dlp as youtube_dl
import os
import sys
import time
import threading
import json
from itertools import cycle
from colorama import Fore, Back, Style, init
from shutil import which
import subprocess

# Initialize colorama 
init(autoreset=True)

# --------------------------
# Constants and Configuration
# --------------------------
CONFIG_FILE = "config.json"
DEFAULT_DOWNLOAD_DIR = os.path.join(os.environ['USERPROFILE'], 'Desktop')
MIN_YT_DLP_VERSION = "2026.02.04"

FFMPEG_MSG = f"""
{Back.RED}{Fore.WHITE} FFMPEG REQUIRED {Style.RESET_ALL}
{Fore.YELLOW}Please install FFmpeg for audio conversions:
1. Download from {Fore.CYAN}https://ffmpeg.org/
2. Add to system PATH
3. Restart this program

------------
Or use the following command:
> winget install ffmpeg
--> And then restart this program
"""

# --------------------------
# Dependency Checks
# --------------------------
def _version_tuple(version_str):
    """Convert a version like '2026.2.4' into a comparable tuple."""
    parts = []
    for chunk in version_str.split('.'):
        try:
            parts.append(int(chunk))
        except ValueError:
            break
    while len(parts) < 3:
        parts.append(0)
    return tuple(parts[:3])


def ensure_recent_yt_dlp():
    """
    Fail fast when yt-dlp is outdated, because old builds break on YouTube's
    rolling signature changes (nsig errors / empty downloads).
    If outdated, try to upgrade in-place and ask for a restart.
    """
    current = youtube_dl.version.__version__
    if _version_tuple(current) < _version_tuple(MIN_YT_DLP_VERSION):
        print(f"{Back.RED}{Fore.WHITE} UPDATE REQUIRED {Style.RESET_ALL}")
        print(f"{Fore.YELLOW}Installed yt-dlp {current} is older than required {MIN_YT_DLP_VERSION}.{Style.RESET_ALL}")
        try:
            subprocess.check_call([
                sys.executable, "-m", "pip", "install", f"yt-dlp>={MIN_YT_DLP_VERSION}"
            ])
            print(f"{Fore.GREEN}yt-dlp updated. Please restart the downloader.{Style.RESET_ALL}")
        except Exception as e:
            print(f"{Back.RED}{Fore.WHITE} AUTO-UPDATE FAILED {Style.RESET_ALL} {e}")
            print(f"{Fore.CYAN}Manual fix:{Style.RESET_ALL} {sys.executable} -m pip install --upgrade \"yt-dlp>={MIN_YT_DLP_VERSION}\"")
        sys.exit(1)

# --------------------------
# Animation Utilities
# --------------------------
class Spinner:
    def __init__(self):
        self.spinner = cycle(['⣾', '⣽', '⣻', '⢿', '⡿', '⣟', '⣯', '⣷'])
        self.running = False
        self.thread = None

    def spin(self, message):
        self.running = True
        sys.stdout.write("\033[?25l") 
        while self.running:
            sys.stdout.write(f"\r{Fore.BLUE}{next(self.spinner)}{Style.RESET_ALL} {message}...  ")
            sys.stdout.flush()
            time.sleep(0.1)
        sys.stdout.write("\033[K") 
        sys.stdout.write("\033[?25h")  

    def start(self, message):
        self.thread = threading.Thread(target=self.spin, args=(message,))
        self.thread.start()

    def stop(self):
        self.running = False
        if self.thread:
            self.thread.join()

# --------------------------
# Core Downloader Class
# --------------------------
class YoutubeDownloader:
    def __init__(self):
        self.config = self.load_config()
        self.download_dir = self.config.get('download_dir', DEFAULT_DOWNLOAD_DIR)
        if not os.path.isdir(self.download_dir):
            print(f"{Fore.YELLOW}The download directory in config does not exist. Reverting to default directory.{Style.RESET_ALL}")
            self.download_dir = DEFAULT_DOWNLOAD_DIR
            self.config['download_dir'] = DEFAULT_DOWNLOAD_DIR
            self.save_config()
            time.sleep(1)
            
        self.ydl_opts = {
            'outtmpl': os.path.join(self.download_dir, '%(title)s.%(ext)s'),
            'progress_hooks': [self._progress_hook],
            'noplaylist': True,
        }
        self.spinner = Spinner()
        self.current_status = {}
        self.downloaded_filename = None

    def load_config(self):
        if not os.path.exists(CONFIG_FILE):
            config = {'download_dir': DEFAULT_DOWNLOAD_DIR}
            with open(CONFIG_FILE, 'w') as f:
                json.dump(config, f, indent=4)
            return config
        else:
            with open(CONFIG_FILE, 'r') as f:
                try:
                    config = json.load(f)
                except Exception:
                    config = {'download_dir': DEFAULT_DOWNLOAD_DIR}
            return config

    def save_config(self):
        self.config['download_dir'] = self.download_dir
        with open(CONFIG_FILE, 'w') as f:
            json.dump(self.config, f, indent=4)

    def _progress_hook(self, d):
        if d['status'] == 'downloading':
            self.current_status = d
        elif d['status'] == 'finished':
            self.spinner.stop()
            self.downloaded_filename = d.get('filename')
            print(f"\r{Fore.GREEN}✓ Processing complete{Style.RESET_ALL}")

    def _display_header(self):
        os.system('cls' if os.name == 'nt' else 'clear')
        header = f"""
{Fore.BLUE}╭──────────────────────────────────────────╮
{Fore.BLUE}│{Fore.CYAN}          🎬 YOUTUBE DOWNLOADER 🎵         {Fore.BLUE}│
{Fore.BLUE}╰──────────────────────────────────────────╯{Style.RESET_ALL}
        """
        print(header)
        print(f"{Fore.LIGHTBLACK_EX}  Platform: {sys.platform} | Python: {sys.version.split()[0]}{Style.RESET_ALL}\n")

    def _set_download_dir(self):
        self._display_header()
        print(f"{Fore.YELLOW}Current download directory:{Style.RESET_ALL}")
        print(f"{Fore.CYAN}{self.download_dir}{Style.RESET_ALL}")
        change = input(f"\n{Fore.YELLOW}Change directory? (y/n):{Style.RESET_ALL} ").lower()
        
        if change == 'y':
            new_dir = input(f"\n{Fore.YELLOW}Enter new path:{Style.RESET_ALL} ").strip()
            if os.path.isdir(new_dir):
                self.download_dir = new_dir
                self.ydl_opts['outtmpl'] = os.path.join(self.download_dir, '%(title)s.%(ext)s')
                self.save_config()
                print(f"\n{Fore.GREEN}✓ Directory updated and saved to config{Style.RESET_ALL}")
            else:
                print(f"\n{Fore.RED}⚠ Directory not found! Keeping previous setting{Style.RESET_ALL}")
            time.sleep(1)

    def _get_choice(self, prompt, options):
        while True:
            self._display_header()
            print(f"{Fore.YELLOW}{prompt}{Style.RESET_ALL}")
            for i, (emoji, text) in enumerate(options, 1):
                print(f"  {Fore.YELLOW}{i}) {emoji} {text}{Style.RESET_ALL}")
            
            try:
                choice = input(f"\n{Fore.YELLOW}Enter choice (1-{len(options)}):{Style.RESET_ALL} ")
                if 1 <= int(choice) <= len(options):
                    return choice
                raise ValueError
            except (ValueError, KeyError):
                print(f"\n{Back.RED}{Fore.WHITE} ERROR {Style.RESET_ALL} Invalid choice!")
                time.sleep(1)

    def _get_url(self):
        self._display_header()
        return input(f"{Fore.YELLOW}🎯 Enter video URL:{Style.RESET_ALL} ").strip()

    def _confirm_download(self, info):
        self._display_header()
        print(f"{Fore.YELLOW}📄 Video Details:{Style.RESET_ALL}")
        print(f"  {Fore.CYAN}▸ Title: {info.get('title', 'N/A')}{Style.RESET_ALL}")
        duration = info.get('duration')
        if duration:
            minutes, seconds = divmod(duration, 60)
            duration_string = f"{minutes}m {seconds}s"
        else:
            duration_string = "N/A"
        print(f"  {Fore.CYAN}▸ Duration: {duration_string}{Style.RESET_ALL}")
        print(f"  {Fore.CYAN}▸ Channel: {info.get('uploader', 'N/A')}{Style.RESET_ALL}")
        
        if filesize := info.get('filesize') or info.get('filesize_approx'):
            size_mb = filesize / (1024 * 1024)
            print(f"  {Fore.CYAN}▸ Size: {size_mb:.1f} MB{Style.RESET_ALL}")
        
        return input(f"\n{Fore.YELLOW}🚀 Start download? (y/n):{Style.RESET_ALL} ").lower() == 'y'

    def _set_format(self, choice):
        format_options = {
            '1': {'format': 'bestaudio/best', 'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192'}]},
            '2': {'format': 'bestaudio/best'},
            '3': {'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best'},
            '4': {'format': 'bestvideo+bestaudio/best'}
        }
        self.ydl_opts.update(format_options[choice])

    def _validate_ffmpeg(self):
        if not which('ffmpeg'):
            print(FFMPEG_MSG)
            sys.exit(1)

    def download_video(self):
        try:
            self._validate_ffmpeg()
            self._display_header()
            self._set_download_dir()

            format_options = [
                ("🎵", "MP3 Audio (High Quality)"),
                ("🎵", "WEBM Audio (Original Quality)"),
                ("📹", "MP4 Video+Audio (Recommended)"),
                ("📹", "WEBM Video+Audio (Best Quality)")
            ]
            choice = self._get_choice("📦 Select download format:", format_options)
            self._set_format(choice)

            url = self._get_url()

            with youtube_dl.YoutubeDL(self.ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)

            if not self._confirm_download(info):
                print(f"\n{Fore.YELLOW}🚫 Download canceled{Style.RESET_ALL}")
                return

            self.spinner.start("Downloading")
            with youtube_dl.YoutubeDL(self.ydl_opts) as ydl:
                ydl.download([url])

            print(f"\n{Fore.GREEN}✓ Download successful!{Style.RESET_ALL}")
            if self.downloaded_filename:
                print(f"{Fore.CYAN}▶ File saved to:{Style.RESET_ALL}")
                print(f"{Fore.LIGHTBLACK_EX}{self.downloaded_filename}{Style.RESET_ALL}")
                self._post_download_options()
        except youtube_dl.DownloadError as e:
            self.spinner.stop()
            print(f"\n{Back.RED}{Fore.WHITE} ERROR {Style.RESET_ALL} {str(e)}")
        except KeyboardInterrupt:
            self.spinner.stop()
            print(f"\n{Fore.YELLOW}⚠ Operation canceled{Style.RESET_ALL}")
        except Exception as e:
            self.spinner.stop()
            print(f"\n{Back.RED}{Fore.WHITE} UNEXPECTED ERROR {Style.RESET_ALL} {str(e)}")
        finally:
            input(f"\n{Fore.LIGHTBLACK_EX}👋 Press Enter to return to menu...{Style.RESET_ALL}")

    def _post_download_options(self):
        while True:
            self._display_header()
            print(f"{Fore.YELLOW}What would you like to do next?{Style.RESET_ALL}")
            options = [
                ("📂", "Open containing folder"),
                ("▶", "Open downloaded file"),
                ("❌", "Do nothing")
            ]
            for i, (emoji, text) in enumerate(options, 1):
                print(f"  {Fore.YELLOW}{i}) {emoji} {text}{Style.RESET_ALL}")
            try:
                choice = input(f"\n{Fore.YELLOW}Enter choice (1-{len(options)}):{Style.RESET_ALL} ")
                if int(choice) == 1:
                    folder = os.path.dirname(self.downloaded_filename)
                    try:
                        os.startfile(folder)
                    except AttributeError:
                        subprocess.call(["xdg-open", folder])
                    break
                elif int(choice) == 2:
                    try:
                        os.startfile(self.downloaded_filename)
                    except AttributeError:
                        subprocess.call(["xdg-open", self.downloaded_filename])
                    break
                elif int(choice) == 3:
                    break
                else:
                    raise ValueError
            except (ValueError, KeyError):
                print(f"\n{Back.RED}{Fore.WHITE} ERROR {Style.RESET_ALL} Invalid choice!")
                time.sleep(1)

# --------------------------
# Main Execution Loop
# --------------------------
def main():
    ensure_recent_yt_dlp()
    downloader = YoutubeDownloader()
    while True:
        downloader.download_video()
        downloader._display_header()
        again = input(f"\n{Fore.YELLOW}Do you want to download another video? (y/n):{Style.RESET_ALL} ").lower()
        if again != 'y':
            print(f"\n{Fore.CYAN}Goodbye!{Style.RESET_ALL}")
            break

if __name__ == "__main__":
    main()
