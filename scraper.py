from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup
import time
import re

class AnimeScraper:
    def __init__(self, headless=True):
        self.headless = headless
        self.base_url = "https://aniwatchtv.to"
        self.playwright = None
        self.browser = None
        self.context = None
        self.page = None

    def start(self):
        self.playwright = sync_playwright().start()
        self.browser = self.playwright.chromium.launch(headless=self.headless)
        self.context = self.browser.new_context()
        self.page = self.context.new_page()
        # Navigate to home to set cookies/headers
        try:
            self.page.goto(self.base_url)
        except Exception as e:
            print(f"Error navigating to base URL: {e}")

    def stop(self):
        if self.context:
            self.context.close()
        if self.browser:
            self.browser.close()
        if self.playwright:
            self.playwright.stop()

    def search(self, query):
        """
        Search for anime by query string.
        Returns a list of dicts: {'title': str, 'id': str, 'url': str}
        """
        # Using the AJAX search endpoint is faster and usually works
        # endpoint: /ajax/search/suggest?keyword=...
        if not self.page:
            self.start()
        
        url = f"{self.base_url}/ajax/search/suggest?keyword={query}"
        # We navigate to a dummy page first or just use API request context? 
        # Easier to just goto the home page once to set cookies etc, then fetch.
        # But actually request_context is better.
        
        # improving robustness: use the page to fetch to share session
        response = self.page.request.get(url)
        if not response.ok:
            print("Search failed.")
            return []
            
        data = response.json()
        html = data.get("html", "")
        soup = BeautifulSoup(html, "html.parser")
        
        results = []
        # Parse the HTML fragment
        for item in soup.find_all("a", class_="nav-item"):
            # href example: /one-piece-movie-1-3096?ref=search
            href = item.get("href")
            # Extract ID
            # clean href
            clean_href = href.split("?")[0] # /one-piece-movie-1-3096
            anime_id = clean_href.split("-")[-1]
            
            # Title
            title_div = item.find("h3", class_="film-name")
            title = title_div.text.strip() if title_div else "Unknown"
            
            # Metadata
            meta_div = item.find("div", class_="film-infor")
            meta = meta_div.text.strip() if meta_div else ""
            
            results.append({
                "title": f"{title} ({meta})",
                "id": anime_id,
                "url": f"{self.base_url}{clean_href}"
            })
            
        return results

    def get_episodes(self, anime_id):
        """
        Get all episodes for a given anime ID.
        """
        if not self.page:
            self.start()
            
        # API: /ajax/v2/episode/list/{anime_id}
        url = f"{self.base_url}/ajax/v2/episode/list/{anime_id}"
        # Set Referer to anime page (approximate)
        headers = {"Referer": f"{self.base_url}/one-piece-{anime_id}"} 
        response = self.page.request.get(url, headers=headers)
        if not response.ok:
            print(f"Episode list request failed: {response.status}")
            return []
            
        data = response.json()
        html = data.get("html", "")
        if not html:
            print(f"No HTML in episode data: {data}")
        
        soup = BeautifulSoup(html, "html.parser")
        
        episodes = []
        # format: <a href="..." data-id="..." data-number="...">
        
        for a in soup.find_all("a", class_="ep-item"):
            ep_id = a.get("data-id")
            ep_num = a.get("data-number")
            title = a.get("title", "")
            is_filler = "ssl-item-filler" in a.get("class", [])
            
            episodes.append({
                "id": ep_id,
                "number": ep_num,
                "title": title,
                "filler": is_filler
            })
            
        return episodes

    def get_sources(self, episode_id):
        """
        Get source links (m3u8) and subtitles.
        """
        if not self.page:
            self.start()
            
        # 1. Get Servers
        url = f"{self.base_url}/ajax/v2/episode/servers?episodeId={episode_id}"
        res = self.page.request.get(url)
        data = res.json()
        html = data.get("html", "")
        soup = BeautifulSoup(html, "html.parser")
        
        servers = soup.find_all("div", class_="server-item")
        print(f"Available servers: {[s.text.strip() for s in servers]}")
        
        # Priority list
        priorities = ["VidStreaming", "VidCloud", "MegaCloud", "StreamSB"]
        
        # Sort servers by priority
        candidate_servers = []
        for p in priorities:
            for s in servers:
                if p.lower() in s.text.strip().lower():
                    candidate_servers.append(s)
        
        # Add remaining servers
        for s in servers:
            if s not in candidate_servers:
                candidate_servers.append(s)
        
        for server in candidate_servers:
            server_name = server.text.strip()
            server_id = server.get("data-id")
            print(f"Trying Server: {server_name}")
            
            result = self._extract_from_server(server_id)
            if result and result['video']:
                return result
                
        print("No playable sources found.")
        return None

    def _extract_from_server(self, server_id):
        url_sources = f"{self.base_url}/ajax/v2/episode/sources?id={server_id}"
        try:
            res_sources = self.page.request.get(url_sources)
            data_sources = res_sources.json()
        except:
            return None
        
        link = data_sources.get("link")
        if not link:
            return None
            
        print(f"Resolving source from embed: {link}")
        
        m3u8_url = None
        subtitles = []
        
        def handle_response(response):
            nonlocal m3u8_url
            if ".m3u8" in response.url and "master" in response.url:
                print(f"Found master m3u8: {response.url}")
                m3u8_url = response.url
            elif ".m3u8" in response.url and not m3u8_url:
                print(f"Found m3u8: {response.url}")
                m3u8_url = response.url

        page = self.context.new_page()
        page.on("response", handle_response)
        try:
            # Set Referer to trick the server
            page.set_extra_http_headers({"Referer": self.base_url})
            
            page.goto(link)
            
            # Save HTML for debugging
            # with open(f"debug_embed_{server_id}.html", "w", encoding="utf-8") as f:
            #     f.write(page.content())
            
            # Method 1: Try to extract via API (MegaCloud/RapidCloud specific)
            if "megacloud" in link or "rapid" in link:
                try:
                    # Extract data-id
                    # Select div with class fix-area or matching id
                    element = page.query_selector("div.fix-area")
                    if element:
                        data_id = element.get_attribute("data-id")
                        if data_id:
                            print(f"Found MegaCloud ID: {data_id}")
                            # Construct API URL
                            # link: https://megacloud.blog/embed-2/v3/e-1/KPBl9iTXPHCD?k=1
                            # api: https://megacloud.blog/embed-2/ajax/e-1/getSources?id=KPBl9iTXPHCD
                            
                            # Parse base url from link
                            import urllib.parse
                            parsed = urllib.parse.urlparse(link)
                            # scheme=https, netloc=megacloud.blog, path=/embed-2/v3/e-1/...
                            # We want path up to /embed-2
                            path_parts = parsed.path.split("/")
                            # path_parts = ['', 'embed-2', 'v3', 'e-1', ...]
                            if 'embed-2' in path_parts:
                                idx = path_parts.index('embed-2')
                                base_path = "/".join(path_parts[:idx+1]) # /embed-2
                                api_url = f"{parsed.scheme}://{parsed.netloc}{base_path}/ajax/e-1/getSources?id={data_id}"
                                
                                print(f"Fetching API: {api_url}")
                                # New request from page context (with headers)
                                headers = {
                                    "X-Requested-With": "XMLHttpRequest",
                                    "Referer": link
                                }
                                api_res = page.request.get(api_url, headers=headers)
                                if api_res.ok:
                                    print(f"API Response: {api_res.text[:500]}") # Debug
                                    data = api_res.json()
                                    # data: {sources: [...], tracks: [...], encrypted: bool}
                                    if data.get("encrypted"):
                                        print("Sources are encrypted. Fallback to network capture.")
                                    else:
                                        srcs = data.get("sources", [])
                                        if srcs:
                                            # Pick first m3u8
                                            for src in srcs:
                                                if src.get("type") == "hls" or ".m3u8" in src.get("file", ""):
                                                    m3u8_url = src.get("file")
                                                    print(f"Found m3u8 via API: {m3u8_url}")
                                                    subtitles = data.get("tracks", [])
                                                    break
                except Exception as e:
                    print(f"API extraction failed: {e}")
            
            # Method 2: Network capture (fallback)
            if not m3u8_url:
                # Try generic play buttons
                selectors = [".play-button", ".jw-display-icon-container", "video", ".btn-play"]
                for sel in selectors:
                    try:
                        if page.is_visible(sel):
                            page.click(sel, timeout=500)
                            break
                    except:
                        pass
                page.wait_for_timeout(5000)
                
        except Exception as e:
            print(f"Error extracting from embed: {e}")
        finally:
            page.close()
            
        if m3u8_url:
            return {"video": m3u8_url, "subs": subtitles}
        return None
