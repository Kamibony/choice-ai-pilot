from fastapi import FastAPI
import os

app = FastAPI()

@app.get("/")
def read_root():
    return {"status": "CHOICE AI is running", "platform": "Google Cloud Run"}

@app.get("/run-pilot")
async def run_pilot():
    return {"message": "Audit started", "target": "CZU Pilot (Placeholder)"}
