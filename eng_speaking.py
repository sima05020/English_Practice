import threading
import time

import requests
import webview

from app import app


def run_flask():
    app.run(debug=False, use_reloader=False)


def wait_for_server(url, timeout=30):
    """サーバーが立ち上がるまで待つ"""
    start = time.time()
    while time.time() - start < timeout:
        try:
            r = requests.get(url)
            if r.status_code == 200:
                return True
        except Exception:
            pass
        time.sleep(0.5)
    raise RuntimeError("Flask server did not start in time")


if __name__ == "__main__":
    flask_thread = threading.Thread(target=run_flask)
    flask_thread.daemon = True
    flask_thread.start()

    wait_for_server("http://127.0.0.1:5000/")

    window = webview.create_window("AI英会話練習", "http://127.0.0.1:5000/")

    def maximize():
        window.maximize()

    # func に max
    webview.start(maximize)
