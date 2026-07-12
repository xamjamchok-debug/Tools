from fastapi import FastAPI

app = FastAPI(title="Agentic Depot", version="0.1.0")


@app.get("/")
def root():
    return {"app": "agentic-depot", "status": "ok"}
