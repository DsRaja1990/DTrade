import json
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import os

CONFIG_FILE = "dhan_config.json"
app = FastAPI()

class TokenRequest(BaseModel):
    access_token: str

def get_token():
    if not os.path.exists(CONFIG_FILE):
        return None
    with open(CONFIG_FILE, "r") as f:
        return json.load(f).get("dhan_access_token")

def set_token(token: str):
    config = {}
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r") as f:
            config = json.load(f)
    config["dhan_access_token"] = token
    with open(CONFIG_FILE, "w") as f:
        json.dump(config, f, indent=2)

@app.post("/update_token")
def update_token(req: TokenRequest):
    set_token(req.access_token)
    return {"status": "success"}

@app.get("/get_token")
def read_token():
    token = get_token()
    if not token:
        raise HTTPException(status_code=404, detail="Token not set")
    return {"access_token": token}
