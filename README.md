# Web Anime CLI

A powerful, terminal-based anime streaming and downloading tool. Watch your favorite series directly in your browser or download them for offline viewing, all from a clean command-line interface.

## 🚀 Features

*   **Stream & Download**: Watch episodes instantly in your local browser (using a custom Flask proxy) while they download in the background.
*   **Search & Browse**: Search for anime and browse episode lists directly from the terminal.
*   **Auto-Subtitles**: Automatically fetches and loads English subtitles (`.vtt`).
*   **Persistent History**: Keeps track of what you've watched. Type `history` to see your log.
*   **"Next" Command**: Finished an episode? Type `next` to automatically load the next one.
*   **Smart Cleanup**: Automatically cleans up downloaded files on exit to save disk space.
*   **Ad-Free**: Bypasses ads and popups by extracting the direct HLS stream.

## 🛠️ Installation

1.  **Clone the repository**:
    ```bash
    git clone https://github.com/Werd342/web-anime-cli.git
    cd web-anime-cli
    ```

2.  **Install Dependencies**:
    ```bash
    pip install -r requirements.txt
    ```

3.  **Install Playwright Browsers**:
    This tool uses Playwright to navigate protected pages.
    ```bash
    playwright install chromium
    ```

## 📖 Usage

Run the main script:

```bash
python main.py
```

### Commands
*   **Search**: Just type the name of the anime.
*   **`history`**: View your verified watch history.
*   **`next`**: Play the next episode of the last series you watched.
*   **`clean`**: Manually wipe the downloads folder.
*   **`q`**: Quit the application.

## ⚠️ Disclaimer

This tool is for **educational purposes only**. It scrapes content from third-party websites. The developers of this tool do not host any content and are not responsible for how this tool is used. Please respect copyright laws in your jurisdiction and support the official releases of anime whenever possible.

## 📄 License

[MIT](LICENSE)
