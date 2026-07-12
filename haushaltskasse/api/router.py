from fastapi import FastAPI

app = FastAPI(title="Haushaltskasse", version="0.1.0")


@app.get("/")
def root():
    return {"app": "haushaltskasse", "status": "ok"}
