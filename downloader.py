from yt_dlp import YoutubeDL
import os
import requests

class GogoDownloader:
    def __init__(self, download_dir="downloads"):
        self.download_dir = download_dir
        if not os.path.exists(download_dir):
            os.makedirs(download_dir)

    def download(self, stream_url, referer, filename, subs=None):
        """
        Downloads the video from the stream_url using yt-dlp.
        Also downloads subtitles if provided.
        """
        output_path = os.path.join(self.download_dir, filename)
        
        # Ensure filename ends with mp4
        if not filename.endswith(".mp4"):
            output_path += ".mp4"

        print(f"Starting download: {filename}")
        
        # Download Subtitles first (or parallel)
        if subs:
            # Prefer English
            target_sub = next((s for s in subs if "English" in s['lang']), subs[0])
            sub_url = target_sub['url']
            sub_ext = sub_url.split(".")[-1] # vtt usually
            sub_filename = output_path.replace(".mp4", f".{sub_ext}")
            
            print(f"Downloading subtitle ({target_sub['lang']}): {sub_filename}...")
            try:
                r = requests.get(sub_url)
                if r.status_code == 200:
                    with open(sub_filename, 'wb') as f:
                        f.write(r.content)
                    print("Subtitle downloaded.")
                else:
                    print(f"Failed to download subtitle: {r.status_code}")
            except Exception as e:
                print(f"Subtitle download error: {e}")
        
        ydl_opts = {
            'format': 'best',
            'outtmpl': output_path,
            'quiet': False,
            'no_warnings': True,
            'http_headers': {
                'Referer': referer,
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            },
            'progress_hooks': [self._progress_hook],
        }
        
        try:
            with YoutubeDL(ydl_opts) as ydl:
                ydl.download([stream_url])
            print("\nDownload complete!")
            return True
        except Exception as e:
            print(f"\nDownload failed: {e}")
            return False

    def _progress_hook(self, d):
        if d['status'] == 'downloading':
            p = d.get('_percent_str', '0%')
            s = d.get('_speed_str', 'N/A')
            e = d.get('_eta_str', 'N/A')
            print(f"\rDownloading: {p} | Speed: {s} | ETA: {e}", end="")
        elif d['status'] == 'finished':
            print("\nDownload finished, finalizing...")

if __name__ == "__main__":
    pass
