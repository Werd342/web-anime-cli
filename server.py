from flask import Flask, request, Response, render_template, jsonify
from flask_cors import CORS
import requests
import os
import signal

app = Flask(__name__)
CORS(app)

PORT = 5000

@app.route('/')
def index():
    url = request.args.get('url')
    subs = request.args.get('subs')
    return render_template('player.html', url=url, subs=subs)

@app.route('/proxy')
def proxy():
    url = request.args.get('url')
    referer = request.args.get('referer', 'https://anitaku.to/')
    
    if not url:
        return "Missing URL", 400

    headers = {
        'Referer': referer,
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }

    try:
        resp = requests.get(url, headers=headers, stream=True)
        
        # Check if it's a playlist (m3u8) by content sniffing
        # Gogoanime URLs might have query params preventing endswith check
        # Checking first few bytes for #EXTM3U is safest
        
        content_sample = resp.content[:10].decode('utf-8', errors='ignore')
        is_m3u8 = '#EXTM3U' in content_sample

        if is_m3u8:
            content = resp.text
            # Rewrite URLs in the m3u8 content
            # M3U8 lines that are not comments (#) are URIs.
            # We need to wrap them in our proxy.
            
            # Helper to encode
            from urllib.parse import quote, urljoin
            
            new_lines = []
            
            for line in content.splitlines():
                if line.strip() and not line.startswith('#'):
                    # It's a URL
                    target_url = line.strip()
                    # Resolve relative URLs safely (handles root-relative / and relative paths)
                    full_url = urljoin(url, target_url)
                    
                    # Encode for proxy
                    safe_url = quote(full_url)
                    safe_referer = quote(referer)
                    new_line = f"/proxy?url={safe_url}&referer={safe_referer}"
                    new_lines.append(new_line)
                else:
                    new_lines.append(line)
            
            new_content = "\n".join(new_lines)
            
            # Return rewriten content
            excluded_headers = ['content-encoding', 'content-length', 'transfer-encoding', 'connection']
            headers_list = [(name, value) for (name, value) in resp.raw.headers.items()
                       if name.lower() not in excluded_headers]
            
            return Response(new_content, status=resp.status_code, headers=headers_list)

        else:
            # Binary/Stream pass-through
            excluded_headers = ['content-encoding', 'content-length', 'transfer-encoding', 'connection']
            headers = [(name, value) for (name, value) in resp.raw.headers.items()
                       if name.lower() not in excluded_headers]

            return Response(resp.iter_content(chunk_size=1024),
                            status=resp.status_code,
                            headers=headers)
    except Exception as e:
        return str(e), 500

@app.route('/shutdown', methods=['POST'])
def shutdown():
    os.kill(os.getpid(), signal.SIGTERM)
    return jsonify({"status": "Server shutting down..."})

if __name__ == '__main__':
    print(f"Starting server on http://localhost:{PORT}")
    app.run(port=PORT, debug=False, threaded=True)
