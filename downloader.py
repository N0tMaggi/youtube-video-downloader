import os
import sys
import time
import json
import subprocess
from shutil import which
from typing import Optional, Dict, Any

import yt_dlp as youtube_dl
import questionary
from questionary import Style as QStyle
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.progress import (
    Progress,
    SpinnerColumn,
    BarColumn,
    TextColumn,
    DownloadColumn,
    TransferSpeedColumn,
    TimeRemainingColumn
)
from rich import box

# --------------------------
# Global Setup & Styling
# --------------------------
console = Console()

custom_style = QStyle([
    ('qmark', 'fg:#00ffff bold'),
    ('question', 'bold fg:#ffffff'),
    ('answer', 'fg:#00ff88 bold'),
    ('pointer', 'fg:#ff007f bold'),
    ('highlighted', 'fg:#00ffff bold'),
    ('selected', 'fg:#00ff88'),
    ('separator', 'fg:#888888'),
    ('instruction', 'fg:#aaaaaa italic'),
    ('text', 'fg:#ffffff'),
])

CONFIG_FILE = "config.json"
DEFAULT_DOWNLOAD_DIR = os.path.join(os.environ.get('USERPROFILE', ''), 'Desktop')
MIN_YT_DLP_VERSION = "2026.02.04"

BROWSER_DEFS = {
    'firefox': {
        'name': 'Firefox',
        'icon': '🦊',
        'exe': 'firefox.exe',
        'paths': [
            os.path.join(os.environ.get('APPDATA', ''), 'Mozilla', 'Firefox', 'Profiles')
        ],
        'note': 'Recommended (works reliably even while browser is open)'
    },
    'brave': {
        'name': 'Brave',
        'icon': '🦁',
        'exe': 'brave.exe',
        'paths': [
            os.path.join(os.environ.get('LOCALAPPDATA', ''), 'BraveSoftware', 'Brave-Browser', 'User Data')
        ],
        'note': 'Chromium (temporarily close browser if cookie lock error occurs)'
    },
    'chrome': {
        'name': 'Google Chrome',
        'icon': '🌐',
        'exe': 'chrome.exe',
        'paths': [
            os.path.join(os.environ.get('LOCALAPPDATA', ''), 'Google', 'Chrome', 'User Data'),
            os.path.join(os.environ.get('ProgramFiles', ''), 'Google', 'Chrome'),
            os.path.join(os.environ.get('ProgramFiles(x86)', ''), 'Google', 'Chrome')
        ],
        'note': 'Chromium'
    },
    'edge': {
        'name': 'Microsoft Edge',
        'icon': '🌊',
        'exe': 'msedge.exe',
        'paths': [
            os.path.join(os.environ.get('LOCALAPPDATA', ''), 'Microsoft', 'Edge', 'User Data')
        ],
        'note': 'Chromium'
    },
    'opera': {
        'name': 'Opera',
        'icon': '🔴',
        'exe': 'opera.exe',
        'paths': [
            os.path.join(os.environ.get('APPDATA', ''), 'Opera Software', 'Opera Stable')
        ],
        'note': 'Chromium'
    },
    'opera_gx': {
        'name': 'Opera GX',
        'icon': '🎮',
        'exe': 'opera.exe',
        'paths': [
            os.path.join(os.environ.get('APPDATA', ''), 'Opera Software', 'Opera GX Stable')
        ],
        'note': 'Chromium'
    },
    'vivaldi': {
        'name': 'Vivaldi',
        'icon': '🧭',
        'exe': 'vivaldi.exe',
        'paths': [
            os.path.join(os.environ.get('LOCALAPPDATA', ''), 'Vivaldi', 'User Data')
        ],
        'note': 'Chromium'
    },
    'chromium': {
        'name': 'Chromium',
        'icon': '⚡',
        'exe': 'chromium.exe',
        'paths': [
            os.path.join(os.environ.get('LOCALAPPDATA', ''), 'Chromium', 'User Data')
        ],
        'note': 'Chromium'
    }
}

# --------------------------
# Helper Utilities
# --------------------------
def _version_tuple(version_str: str):
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
    current = youtube_dl.version.__version__
    if _version_tuple(current) < _version_tuple(MIN_YT_DLP_VERSION):
        console.print(Panel(
            f"[bold red]UPDATE REQUIRED[/bold red]\n"
            f"Installed yt-dlp ({current}) is older than required ({MIN_YT_DLP_VERSION}).\n"
            f"Upgrading automatically...",
            border_style="red"
        ))
        try:
            subprocess.check_call([
                sys.executable, "-m", "pip", "install", f"yt-dlp>={MIN_YT_DLP_VERSION}"
            ])
            console.print("[green]✓ yt-dlp successfully updated. Please restart the script.[/green]")
        except Exception as e:
            console.print(f"[bold red]Auto-update failed:[/bold red] {e}")
        sys.exit(1)


def is_process_running(exe_name: str) -> bool:
    try:
        out = subprocess.run(
            ['tasklist', '/NH', '/FI', f'IMAGENAME eq {exe_name}'],
            capture_output=True,
            text=True,
            timeout=2
        ).stdout
        return exe_name.lower() in out.lower()
    except Exception:
        return False


def is_browser_installed(browser_key: str) -> bool:
    meta = BROWSER_DEFS.get(browser_key)
    if not meta:
        return False
    return any(os.path.exists(p) for p in meta['paths'])

# --------------------------
# Downloader Core
# --------------------------
class YoutubeDownloader:
    def __init__(self):
        self.config = self.load_config()
        self.download_dir = self.config.get('download_dir', DEFAULT_DOWNLOAD_DIR)
        if not os.path.isdir(self.download_dir):
            self.download_dir = DEFAULT_DOWNLOAD_DIR
            self.config['download_dir'] = DEFAULT_DOWNLOAD_DIR
            self.save_config()

        self.browser_cookies = self.config.get('browser_cookies', 'firefox')
        self.downloaded_filename: Optional[str] = None
        self.active_progress: Optional[Progress] = None
        self.download_task_id: Optional[int] = None

    def load_config(self) -> Dict[str, Any]:
        default_config = {
            'download_dir': DEFAULT_DOWNLOAD_DIR,
            'browser_cookies': 'firefox'
        }
        if not os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
                json.dump(default_config, f, indent=4)
            return default_config
        else:
            try:
                with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                    config = json.load(f)
            except Exception:
                config = default_config
            if 'browser_cookies' not in config:
                config['browser_cookies'] = 'firefox'
            return config

    def save_config(self):
        self.config['download_dir'] = self.download_dir
        self.config['browser_cookies'] = self.browser_cookies
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(self.config, f, indent=4)

    def _progress_hook(self, d: Dict[str, Any]):
        if d['status'] == 'downloading':
            total = d.get('total_bytes') or d.get('total_bytes_estimate') or 100
            downloaded = d.get('downloaded_bytes', 0)
            if self.active_progress and self.download_task_id is not None:
                self.active_progress.update(
                    self.download_task_id,
                    total=total,
                    completed=downloaded
                )
        elif d['status'] == 'finished':
            self.downloaded_filename = d.get('filename')
            if self.active_progress and self.download_task_id is not None:
                total = d.get('total_bytes') or self.active_progress.tasks[self.download_task_id].total
                self.active_progress.update(self.download_task_id, completed=total)

    def build_ydl_opts(self, format_choice: str) -> Dict[str, Any]:
        opts: Dict[str, Any] = {
            'outtmpl': os.path.join(self.download_dir, '%(title)s.%(ext)s'),
            'progress_hooks': [self._progress_hook],
            'noplaylist': True,
            'quiet': True,
            'no_warnings': True,
        }

        # Browser cookies
        if self.browser_cookies and self.browser_cookies.lower() not in ['none', 'disabled', '']:
            opts['cookiesfrombrowser'] = (self.browser_cookies.lower(),)

        # JS Challenge Solver
        if which('node'):
            opts['js_runtimes'] = {'node': {}}
            opts['remote_components'] = ['ejs:github']

        # Format mappings
        if format_choice == 'mp4':
            opts['format'] = 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best'
            opts['merge_output_format'] = 'mp4'
        elif format_choice == 'mp3':
            opts['format'] = 'bestaudio/best'
            opts['postprocessors'] = [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }]
        elif format_choice == 'webm_audio':
            opts['format'] = 'bestaudio/best'
        elif format_choice == 'webm_video':
            opts['format'] = 'bestvideo+bestaudio/best'

        return opts

    def show_banner(self):
        console.clear()
        cookies_display = self.browser_cookies.capitalize() if self.browser_cookies and self.browser_cookies != 'none' else "Disabled"
        if self.browser_cookies in BROWSER_DEFS:
            icon = BROWSER_DEFS[self.browser_cookies]['icon']
            cookies_display = f"{icon} {cookies_display}"

        info_table = Table(show_header=False, box=box.SIMPLE, pad_edge=False)
        info_table.add_column("Key", style="bold cyan")
        info_table.add_column("Value", style="bold white")

        info_table.add_row("📁 Download Directory:", self.download_dir)
        info_table.add_row("🍪 Cookie Browser:", cookies_display)
        info_table.add_row("⚡ JS Engine:", "[green]Node.js (Active)[/green]" if which('node') else "[yellow]Not found[/yellow]")
        info_table.add_row("🎵 FFmpeg:", "[green]Ready[/green]" if which('ffmpeg') else "[red]Missing[/red]")

        console.print(Panel(
            info_table,
            title="[bold magenta]🎬 YOUTUBE DOWNLOADER TUI[/bold magenta]",
            subtitle="[italic white]Fast • Reliable • Modern[/italic white]",
            border_style="bright_blue",
            box=box.ROUNDED
        ))

    def select_browser_menu(self):
        self.show_banner()
        choices = []

        for key, meta in BROWSER_DEFS.items():
            installed = is_browser_installed(key)
            running = is_process_running(meta['exe']) if installed else False

            status_tags = []
            if installed:
                status_tags.append("[Installed]")
            if running:
                status_tags.append("[Running]")

            status_str = f" {' '.join(status_tags)}" if status_tags else ""
            title = f"{meta['icon']} {meta['name']}{status_str} — {meta['note']}"
            choices.append(questionary.Choice(title=title, value=key))

        choices.append(questionary.Choice(
            title="❌ Disabled (Do not use browser cookies)",
            value="none"
        ))

        selected = questionary.select(
            "Select browser for YouTube authentication & cookie bypass:",
            choices=choices,
            default=self.browser_cookies if self.browser_cookies in BROWSER_DEFS else 'firefox',
            style=custom_style
        ).ask()

        if selected:
            self.browser_cookies = selected
            self.save_config()
            console.print(f"\n[green]✓ Cookie browser set to [bold]{selected}[/bold].[/green]")
            time.sleep(1)

    def change_directory_menu(self):
        self.show_banner()
        console.print(f"[bold cyan]Current download directory:[/bold cyan] {self.download_dir}\n")

        new_dir = questionary.text(
            "Enter new download directory path (or leave blank to cancel):",
            default=self.download_dir,
            style=custom_style
        ).ask()

        if new_dir and os.path.isdir(new_dir):
            self.download_dir = os.path.abspath(new_dir)
            self.save_config()
            console.print(f"\n[green]✓ Directory updated to: {self.download_dir}[/green]")
        elif new_dir:
            console.print(f"\n[red]⚠ Directory '{new_dir}' not found![/red]")
        time.sleep(1.2)

    def download_flow(self):
        self.show_banner()
        if not which('ffmpeg'):
            console.print(Panel(
                "[bold red]FFmpeg is not installed![/bold red]\n"
                "Please install FFmpeg, e.g. via: [cyan]winget install ffmpeg[/cyan]",
                border_style="red"
            ))
            questionary.press_any_key_to_continue("Press any key to return...").ask()
            return

        url = questionary.text(
            "🎯 Enter YouTube URL:",
            validate=lambda text: True if text.strip() else "Please enter a valid URL",
            style=custom_style
        ).ask()

        if not url:
            return

        url = url.strip()

        # Step 1: Format selection
        format_choices = [
            questionary.Choice(title="📹 MP4 Video + Audio (Recommended - Best Quality)", value="mp4"),
            questionary.Choice(title="🎵 MP3 Audio (192kbps High Quality via FFmpeg)", value="mp3"),
            questionary.Choice(title="🎵 WEBM Audio (Original Audio Track)", value="webm_audio"),
            questionary.Choice(title="📹 WEBM Video + Audio (Original)", value="webm_video")
        ]

        format_choice = questionary.select(
            "📦 Select download format:",
            choices=format_choices,
            style=custom_style
        ).ask()

        if not format_choice:
            return

        opts = self.build_ydl_opts(format_choice)

        # Step 2: Fetch metadata
        self.show_banner()
        info = None
        with console.status("[bold cyan]Fetching video details from YouTube...[/bold cyan]", spinner="dots"):
            try:
                with youtube_dl.YoutubeDL(opts) as ydl:
                    info = ydl.extract_info(url, download=False)
            except Exception as e:
                err_msg = str(e)
                console.print(f"\n[bold red]Error fetching video information:[/bold red] {err_msg}")
                if "Sign in to confirm you" in err_msg or "bot" in err_msg:
                    console.print("\n[yellow]💡 Tip: YouTube flagged automated traffic. Go to 'Cookie Browser' in the main menu and select Firefox (recommended) or your active browser![/yellow]")
                elif "Could not copy Chrome cookie database" in err_msg or "DPAPI" in err_msg:
                    console.print("\n[yellow]💡 Tip: Your selected Chromium browser is open and has locked its cookie database. Close it or switch to Firefox in Cookie Browser settings.[/yellow]")
                questionary.press_any_key_to_continue().ask()
                return

        if not info:
            console.print("[red]Could not retrieve video information.[/red]")
            questionary.press_any_key_to_continue().ask()
            return

        # Step 3: Display Video Details Table
        table = Table(title="📄 Video Details", box=box.ROUNDED, show_header=False)
        table.add_column("Key", style="cyan bold")
        table.add_column("Value", style="white")

        table.add_row("Title", info.get('title', 'N/A'))
        table.add_row("Channel", info.get('uploader', 'N/A'))

        duration = info.get('duration')
        if duration:
            m, s = divmod(duration, 60)
            h, m = divmod(m, 60)
            table.add_row("Duration", f"{h:02d}:{m:02d}:{s:02d}" if h else f"{m:02d}:{s:02d}")
        else:
            table.add_row("Duration", "Unknown")

        if views := info.get('view_count'):
            table.add_row("Views", f"{views:,}")

        if filesize := info.get('filesize') or info.get('filesize_approx'):
            table.add_row("Estimated Size", f"{filesize / (1024 * 1024):.1f} MB")

        console.print(table)

        confirm = questionary.confirm(
            "Start download now?",
            default=True,
            style=custom_style
        ).ask()

        if not confirm:
            console.print("[yellow]Download cancelled.[/yellow]")
            time.sleep(1)
            return

        # Step 4: Live Progress Download
        console.print("\n[bold green]Starting download...[/bold green]")
        self.downloaded_filename = None

        with Progress(
            SpinnerColumn(),
            TextColumn("[bold cyan]{task.description}"),
            BarColumn(bar_width=None),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            DownloadColumn(),
            TransferSpeedColumn(),
            TimeRemainingColumn(),
            console=console
        ) as progress:
            self.active_progress = progress
            self.download_task_id = progress.add_task(f"Downloading: {info.get('title', 'Video')[:35]}...", total=100)

            try:
                with youtube_dl.YoutubeDL(opts) as ydl:
                    ydl.download([url])
            except Exception as e:
                console.print(f"\n[bold red]Download error:[/bold red] {e}")
                questionary.press_any_key_to_continue().ask()
                return
            finally:
                self.active_progress = None
                self.download_task_id = None

        console.print(f"\n[bold green]✓ Download completed successfully![/bold green]")
        if self.downloaded_filename:
            console.print(f"[cyan]Saved to:[/cyan] [bold white]{self.downloaded_filename}[/bold white]\n")

        # Step 5: Post-Download Actions
        post_choices = [
            questionary.Choice("📂 Open destination folder in Explorer", "open_folder"),
            questionary.Choice("▶ Play downloaded file", "open_file"),
            questionary.Choice("🔄 Download another video", "again"),
            questionary.Choice("🔙 Back to main menu", "menu")
        ]

        action = questionary.select(
            "What would you like to do next?",
            choices=post_choices,
            style=custom_style
        ).ask()

        if action == "open_folder":
            folder = os.path.dirname(self.downloaded_filename) if self.downloaded_filename else self.download_dir
            try:
                os.startfile(folder)
            except Exception:
                subprocess.call(["explorer", folder])
        elif action == "open_file":
            if self.downloaded_filename and os.path.exists(self.downloaded_filename):
                try:
                    os.startfile(self.downloaded_filename)
                except Exception:
                    subprocess.call(["explorer", self.downloaded_filename])
        elif action == "again":
            self.download_flow()

    def run(self):
        while True:
            self.show_banner()
            main_choices = [
                questionary.Choice("🚀 Download Video", "download"),
                questionary.Choice("🍪 Select Cookie Browser (Brave, Chrome, Firefox...)", "cookies"),
                questionary.Choice("📁 Change Download Directory", "dir"),
                questionary.Choice("🚪 Exit", "exit")
            ]

            choice = questionary.select(
                "Main Menu (Use arrow keys to navigate):",
                choices=main_choices,
                style=custom_style
            ).ask()

            if choice == "download":
                self.download_flow()
            elif choice == "cookies":
                self.select_browser_menu()
            elif choice == "dir":
                self.change_directory_menu()
            elif choice == "exit" or choice is None:
                console.print("\n[bold cyan]Goodbye![/bold cyan]")
                break


def main():
    ensure_recent_yt_dlp()
    app = YoutubeDownloader()
    app.run()


if __name__ == "__main__":
    main()
