import os
import sys

os.chdir(os.path.dirname(os.path.abspath(__file__)))

# Carrega .env antes de qualquer import
from dotenv import load_dotenv
load_dotenv()

# Log pra debug
sys.stdout = open("amanda.log", "w")
sys.stderr = sys.stdout

import threading
import uvicorn
import webview
from app import app

def start_server():
    uvicorn.run(app, host="127.0.0.1", port=8000, log_level="warning")

server_thread = threading.Thread(target=start_server, daemon=True)
server_thread.start()

# Espera o servidor subir
import time
time.sleep(2)

webview.create_window(
    "Amanda",
    "http://127.0.0.1:8000",
    width=420,
    height=720,
    resizable=True,
    min_size=(360, 500),
    x=None,
    y=30,
)
webview.start()
