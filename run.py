import subprocess
import sys
import webbrowser
from time import sleep

def main():
    # Start backend server
    backend = subprocess.Popen([sys.executable, "-m", "uvicorn", "main:app", "--host", "127.0.0.1", "--port", "3000"])
    
    # Start frontend server
    frontend = subprocess.Popen([sys.executable, "-m", "http.server", "8000"])
    
    # Wait a moment for servers to start
    sleep(2)
    
    # Open browser
    webbrowser.open('http://localhost:8000')
    
    try:
        # Keep the script running
        backend.wait()
        frontend.wait()
    except KeyboardInterrupt:
        # Handle Ctrl+C gracefully
        backend.terminate()
        frontend.terminate()
        print("\nServers stopped")

if __name__ == "__main__":
    main() 