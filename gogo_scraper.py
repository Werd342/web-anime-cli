from playwright.sync_api import sync_playwright
import time
import urllib.parse
import re

class GogoScraper:
    def __init__(self, headless=True):
        self.headless = headless
        self.base_url = "https://anitaku.to"
        self._playwright = None
        self._browser = None
        self._page = None

    def start(self):
        """Starts the Playwright browser."""
        if not self._playwright:
            self._playwright = sync_playwright().start()
            self._browser = self._playwright.chromium.launch(headless=self.headless)
            self._page = self._browser.new_page()

    def close(self):
        """Closes the Playwright browser."""
        if self._browser:
            self._browser.close()
            self._browser = None
        if self._playwright:
            self._playwright.stop()
            self._playwright = None

    def search(self, query):
        """
        Searches for anime.
        Returns a list of dicts: {'title': str, 'url': str}
        """
        self.start()
        print(f"Searching for '{query}'...")
        search_url = f"{self.base_url}/search.html?keyword={urllib.parse.quote(query)}"
        
        try:
            self._page.goto(search_url, wait_until="domcontentloaded")
            self._page.wait_for_selector(".items li", timeout=10000)
            
            results = []
            elements = self._page.query_selector_all(".items li")
            
            for elem in elements:
                name_tag = elem.query_selector(".name a")
                if name_tag:
                    title = name_tag.text_content().strip()
                    href = name_tag.get_attribute("href")
                    # Ensure full URL
                    if href.startswith("/"):
                        href = self.base_url + href
                    results.append({"title": title, "url": href})
            
            return results
        except Exception as e:
            print(f"Search failed: {e}")
            return []

    def get_episode_count(self, category_url):
        """
        Gets the total number of episodes for an anime.
        """
        self.start()
        print(f"Fetching episode count from {category_url}...")
        try:
            self._page.goto(category_url, wait_until="domcontentloaded")
            self._page.wait_for_selector("#episode_page", timeout=10000)
            
            # Gogoanime lists ranges. Check 'ep_end' first, then 'data-value'.
            ep_ranges = self._page.query_selector_all("#episode_page li a")
            if ep_ranges:
                last_elem = ep_ranges[-1]
                ep_end = last_elem.get_attribute("ep_end")
                if ep_end:
                    return int(ep_end)
                
                # Fallback: parse data-value="301-366"
                data_val = last_elem.get_attribute("data-value") # e.g. "301-366"
                if data_val and "-" in data_val:
                    try:
                        end_val = data_val.split("-")[-1]
                        return int(end_val)
                    except:
                        pass
            
            # If no ranges found or failed, check for single page execution?
            # Or maybe check the episode list itself #episode_related li
            # But episode list is loaded dynamically based on range selection.
            # Default to 0 or investigate.
            return 0
        except Exception as e:
            print(f"Failed to get episode count: {e}")
            return 0

    def get_stream_url(self, episode_url):
        """
        Extracts the HLS stream URL (master.txt/m3u8) for an episode.
        Returns: {'url': str, 'referer': str} or None
        """
        self.start()
        print(f"Extracting stream from {episode_url}...")
        
        # 1. Go to episode page
        try:
            self._page.goto(episode_url, wait_until="domcontentloaded")
            
            # 2. Find iframe
            iframe = self._page.query_selector("iframe")
            if not iframe:
                print("No video iframe found.")
                return None
            
            src = iframe.get_attribute("src")
            # Ensure protocol
            if src.startswith("//"):
                src = "https:" + src
            
            print(f"Found embed source: {src}")
            
            # Extract subtitles from URL params
            subtitles = []
            try:
                parsed = urllib.parse.urlparse(src)
                params = urllib.parse.parse_qs(parsed.query)
                # Check for caption_1, caption_2, etc.
                # Usually caption_1 and sub_1
                for i in range(1, 10):
                    cap_key = f"caption_{i}"
                    sub_key = f"sub_{i}"
                    if cap_key in params:
                        sub_url = params[cap_key][0]
                        sub_lang = params.get(sub_key, ["English"])[0]
                        subtitles.append({"url": sub_url, "lang": sub_lang})
                
                if subtitles:
                    print(f"Found subtitles: {len(subtitles)}")
            except Exception as e:
                print(f"Subtitle extraction failed: {e}")
            
            # 3. Intercept Network
            master_url = None
            
            def handle_request(req):
                nonlocal master_url
                if not master_url and ("master.txt" in req.url or "master.m3u8" in req.url):
                    master_url = req.url
                    # print(f"Captured: {master_url}") 

            # Listen
            self._page.on("request", handle_request)
            
            try:
                # 4. Visit Embed Page with Referer
                self._page.set_extra_http_headers({"Referer": self.base_url})
                self._page.goto(src, wait_until="domcontentloaded")
                
                # Wait a bit for the player to load and request the manifest
                try:
                    self._page.wait_for_selector("video", timeout=5000)
                except:
                    pass 
                
                # Extra wait for network
                start_time = time.time()
                while not master_url and time.time() - start_time < 5:
                    self._page.wait_for_timeout(500)
                
                if master_url:
                    print(f"Successfully extracted HLS URL: {master_url}")
                    return {"url": master_url, "referer": src, "subs": subtitles}
                else:
                    print("Failed to capture master URL.")
                    return None
            finally:
                # Cleanup listener
                self._page.remove_listener("request", handle_request)

        except Exception as e:
            print(f"Stream extraction failed: {e}")
            return None

        except Exception as e:
            print(f"Stream extraction failed: {e}")
            return None

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

if __name__ == "__main__":
    # Test script
    scraper = GogoScraper(headless=True)
    try:
        scraper.start()
        results = scraper.search("bleach")
        if results:
            print(f"Found {len(results)} results. Top: {results[0]['title']}")
            
            # Find the main bleach
            target = next((r for r in results if r['title'].lower() == 'bleach'), results[0])
            print(f"Selected: {target['title']}")
            
            count = scraper.get_episode_count(target['url'])
            print(f"Episode count: {count}")
            
            if count > 0:
                # Construct ep 1 url
                # url: https://anitaku.to/category/bleach -> bleach
                slug = target['url'].split("/")[-1]
                ep_url = f"{scraper.base_url}/{slug}-episode-1"
                
                scan_res = scraper.get_stream_url(ep_url)
                print(f"Stream Result: {scan_res}")
    finally:
        scraper.close()
