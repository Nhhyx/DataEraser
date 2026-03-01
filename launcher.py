import threading, webbrowser, time
from app import app  # ton Flask app

def open_browser():
    time.sleep(1)
    webbrowser.open("http://127.0.0.1:5000")

if __name__ == "__main__":
    threading.Thread(target=open_browser, daemon=True).start()
    app.run(host="127.0.0.1", port=5000)

