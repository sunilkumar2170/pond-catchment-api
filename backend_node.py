import sys
import os
import time
from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
import uvicorn

app = FastAPI()

NODE_ID = os.getenv("NODE_ID", "Sys-Worker")
MESSAGES = []

@app.get("/health")
async def health():
    return {
        "status": "ok",
        "service": "Backend",
        "node_id": NODE_ID,
        "total_clients": len(MESSAGES)
    }

@app.post("/message", status_code=status.HTTP_200_OK)
@app.post("/post", status_code=status.HTTP_200_OK)
async def post_message(request: Request):
    try:
        data = await request.json()
    except Exception:
        data = {}
    MESSAGES.append(data)
    return {"status": "ok", "saved_at": NODE_ID, "count": len(MESSAGES)}

@app.get("/feed")
async def get_feed():
    return {"messages": MESSAGES, "count": len(MESSAGES)}

if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8000
    uvicorn.run(app, host="0.0.0.0", port=port, loop="uvloop", access_log=False)
