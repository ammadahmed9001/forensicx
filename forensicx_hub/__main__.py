"""
Allow `python -m forensicx_hub` to launch the web dashboard.
Falls back to the Tkinter hub if Flask is unavailable.
"""
import sys

def main():
    web = "--web" in sys.argv
    tkinter_mode = "--tkinter" in sys.argv

    if tkinter_mode:
        from forensicx_hub.app import run_hub
        run_hub()
        return

    try:
        from forensicx_hub.web_app import run_web
        port = 5000
        for a in sys.argv[1:]:
            if a.startswith("--port="):
                port = int(a.split("=")[1])
        run_web(port=port)
    except ImportError:
        print("[WARN] Flask not installed — falling back to Tkinter hub")
        print("       pip install flask flask-socketio  to enable the web dashboard")
        from forensicx_hub.app import run_hub
        run_hub()

main()
