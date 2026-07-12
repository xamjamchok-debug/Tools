"""
Startet alle drei Apps gemeinsam.
Einzeln starten: uvicorn haushaltskasse.api.router:app --port 3000
"""
import subprocess
import sys

APPS = [
    ("haushaltskasse", 3000),
    ("agentic-depot",  3001),
    ("work-journal",   3002),
]

if __name__ == "__main__":
    procs = []
    for name, port in APPS:
        module = name.replace("-", "_")
        p = subprocess.Popen(
            [sys.executable, "-m", "uvicorn", f"{module}.api.router:app", "--port", str(port), "--reload"],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
        )
        procs.append((name, p))
        print(f"[main] {name} gestartet auf Port {port} (PID {p.pid})")

    try:
        for name, p in procs:
            p.wait()
    except KeyboardInterrupt:
        print("\n[main] Stoppe alle Apps…")
        for _, p in procs:
            p.terminate()
