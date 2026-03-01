import threading, webbrowser, time
from app import app
import os

last_ping = time.time()

@app.route("/ping")
def ping():
    global last_ping
    last_ping = time.time()
    return "ok"

def watchdog():
    global last_ping
    while True:
        time.sleep(5)
        if time.time() - last_ping > 15:
            print("Browser closed -> stopping")
            os._exit(0)

def open_browser():
    time.sleep(1)
    webbrowser.open("http://127.0.0.1:5000")

if __name__ == "__main__":
    threading.Thread(target=open_browser, daemon=True).start()
    threading.Thread(target=watchdog, daemon=True).start()
    app.run(host="127.0.0.1", port=5000)