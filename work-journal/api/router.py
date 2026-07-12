from fastapi import FastAPI

app = FastAPI(title="Work Journal", version="0.1.0")


@app.get("/")
def root():
    return {"app": "work-journal", "status": "ok"}
