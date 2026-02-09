from fastapi import FastAPI
from fastapi.testclient import TestClient
import traceback

app = FastAPI()

@app.get("/")
def read_root():
    return {"Hello": "World"}

client = TestClient(app)

try:
    response = client.get("/")
    print(response.json())
except Exception:
    traceback.print_exc()
