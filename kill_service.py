import requests
import sys

def kill_server(port=5000):
    try:
        print(f"Sending shutdown signal to localhost:{port}...")
        requests.post(f"http://localhost:{port}/shutdown", timeout=2)
        print("Shutdown request sent.")
    except requests.exceptions.ConnectionError:
        print("Server appears to be down already.")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    kill_server()
