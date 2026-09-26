"""
AI File Manager - Application Launcher
Starts the FastAPI server and automatically opens the user's default browser.
"""

import sys
import webbrowser
import time
import threading
from pathlib import Path
import uvicorn


def open_browser():
    time.sleep(1.2)
    url = "http://127.0.0.1:8000"
    print(f"\n========================================================")
    print(f">> AI File Manager running at: {url}")
    print(f"   Opening web interface in your default browser...")
    print(f"========================================================\n")
    try:
        webbrowser.open(url)
    except Exception as e:
        print(f"Could not automatically open browser: {e}")


def main():
    # Ensure project root is in sys.path
    project_root = Path(__file__).resolve().parent
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))

    # Spawn browser in separate thread
    threading.Thread(target=open_browser, daemon=True).start()

    # Run FastAPI app with auto-reload
    uvicorn.run("backend.main:app", host="127.0.0.1", port=8000, log_level="info", reload=True)


if __name__ == "__main__":
    main()
