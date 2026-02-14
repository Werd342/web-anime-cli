import sys
from gogo_scraper import GogoScraper
from downloader import GogoDownloader
from utils import sanitize_filename
import subprocess
import webbrowser
import time
import os
import shutil
import json
import urllib.parse

HISTORY_FILE = "history.json"

def load_history():
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, 'r') as f:
                return json.load(f)
        except:
            return []
    return []

def save_history(entry):
    history = load_history()
    # Add timestamp
    entry['timestamp'] = time.ctime()
    history.append(entry)
    # Keep last 50
    if len(history) > 50:
        history = history[-50:]
    
    with open(HISTORY_FILE, 'w') as f:
        json.dump(history, f, indent=4)

def cleanup_downloads():
    download_dir = "downloads"
    if os.path.exists(download_dir):
        print("Cleaning up downloads folder...")
        for filename in os.listdir(download_dir):
            file_path = os.path.join(download_dir, filename)
            try:
                if os.path.isfile(file_path) or os.path.islink(file_path):
                    os.unlink(file_path)
                elif os.path.isdir(file_path):
                    shutil.rmtree(file_path)
            except Exception as e:
                print(f"Failed to delete {file_path}. Reason: {e}")

def main():
    print("Initializing Anime Downloader (Stream & Download Edition)...")
    scraper = GogoScraper(headless=True)
    downloader = GogoDownloader(download_dir="downloads")
    server_process = None
    
    # State for 'next' command
    last_watched = None # {'title': str, 'url': str, 'episode': int}
    
    # Cleanup on start? User said "accumulate over time", so clean on exit is critical. 
    # Clean on start is also good practice for temp files.
    cleanup_downloads()

    try:
        while True:
            # RESET STATE for new iteration
            selected = None
            ep_num = None
            
            # 1. Search / Command Loop
            while not selected:
                query = input("\nSearch anime, 'history', 'next' (or 'q' to quit): ").strip()
                if query.lower() == 'q':
                    raise KeyboardInterrupt
                
                if not query:
                    continue
                
                if query.lower() == 'history':
                    hist = load_history()
                    print("\n--- Recent History ---")
                    for h in reversed(hist[-10:]):
                        print(f"[{h['timestamp']}] {h['title']} - Episode {h['episode']}")
                    continue
                
                if query.lower() == 'next':
                    if last_watched:
                        print(f"Loading next episode for: {last_watched['title']}")
                        selected = {'title': last_watched['title'], 'url': last_watched['url']}
                        ep_num = last_watched['episode'] + 1
                        print(f"Targeting Episode: {ep_num}")
                        break
                    else:
                        print("No session history found. Search for an anime first.")
                        continue
                
                if query.lower() == 'clean':
                    cleanup_downloads()
                    print("Downloads folder accepted.")
                    continue
                
                # Normal Search
                results = scraper.search(query)
                if not results:
                    print("No results found.")
                    continue
                
                print(f"\nFound {len(results)} results:")
                for i, res in enumerate(results):
                    print(f"{i+1}. {res['title']}")
                
                # Select Anime
                try:
                    choice = input("\nSelect anime (number): ").strip()
                    if choice.lower() == 'q':
                        raise KeyboardInterrupt
                    idx = int(choice) - 1
                    if idx < 0 or idx >= len(results):
                        print("Invalid selection.")
                        continue
                    
                    selected = results[idx]
                    print(f"Selected: {selected['title']}")
                    break # To Episode Selection
                    
                except ValueError:
                    print("Invalid input.")
                    continue
            
            # 2. Episode Selection (If not set by 'next')
            if ep_num is None:
                count = scraper.get_episode_count(selected['url'])
                if count == 0:
                    print("Could not retrieve episode count. The Series might be a Movie or unreleased.")
                    retry = input("Try Episode 1 anyway? (y/n): ").lower()
                    if retry != 'y':
                        continue
                    count = 1
                    ep_num = 1
                else:
                    print(f"Total Episodes: {count}")
                    ep_input = input(f"Enter episode number (1-{count}): ").strip()
                    if ep_input.lower() == 'q':
                        raise KeyboardInterrupt
                    try:
                        ep_num = int(ep_input)
                        if ep_num < 1: 
                            print("Invalid episode number.")
                            continue
                    except ValueError:
                        print("Invalid number.")
                        continue
            
            # 3. Process Episode
            # Construct Episode URL
            slug = selected['url'].split("/")[-1]
            ep_url = f"{scraper.base_url}/{slug}-episode-{ep_num}"
            
            # Extract Stream
            print(f"Fetching stream for Episode {ep_num}...")
            stream_data = scraper.get_stream_url(ep_url)
            
            if not stream_data:
                print("Could not find a playable stream for this episode.")
                # Reset last watched so 'next' doesn't get stuck on a broken series? 
                # Or keep it so they can try again? Keep it.
                continue
            
            stream_url = stream_data['url']
            referer = stream_data['referer']
            subs = stream_data.get('subs', [])
            
            print(f"\nReady: {selected['title']} - Episode {ep_num}")
            
            # --- AUTO STREAM LOGIC (Replaces Action Selection) ---
            filename = f"{sanitize_filename(selected['title'])} - Episode {ep_num}.mp4"
            
            print("Starting local streaming server...")
            if os.path.exists("server.py"):
                 try:
                    print("Stopping any existing server...")
                    subprocess.run([sys.executable, "kill_service.py"], check=False)
                    time.sleep(1) # Wait for port release
                 except: 
                     pass
                 
                 print(f"Launching server with: {sys.executable} server.py")
                 server_process = subprocess.Popen([sys.executable, "server.py"])
                 time.sleep(2) # Wait for startup
                 
                 if server_process.poll() is not None:
                     print(f"Server failed to start! Exit code: {server_process.returncode}")
                 else:
                     print("Server seems to be running.")
                 
                 # Prepare URL
                 sub_url = ""
                 if subs:
                      target_sub = next((s for s in subs if "English" in s['lang']), subs[0])
                      sub_url = target_sub['url']
                 
                 safe_url = urllib.parse.quote(stream_url)
                 safe_sub = urllib.parse.quote(sub_url)
                 
                 play_link = f"http://localhost:5000/?url={safe_url}&subs={safe_sub}"
                 print(f"Opening browser to: {play_link}")
                 webbrowser.open(play_link)
            else:
                print("Error: server.py not found. Downloading only.")
            
            print(f"Starting background download to: {filename}")
            success = downloader.download(stream_url, referer, filename, subs=subs)
            
            if success:
                print("Download completed!")
                # Update History & Last Watched ONLY on success (or partial success)
                last_watched = {
                    'title': selected['title'], 
                    'url': selected['url'], 
                    'episode': ep_num
                }
                save_history(last_watched)
                print("History updated. Type 'next' to play the next episode.")
            
    except KeyboardInterrupt:
        print("\nExiting...")
    except Exception as e:
        print(f"\nAn error occurred: {e}")
        import traceback
        traceback.print_exc()
    finally:
        print("Cleaning up...")
        if server_process:
             subprocess.run([sys.executable, "kill_service.py"], check=False)
        
        cleanup_downloads() 
        scraper.close()

if __name__ == "__main__":
    main()
