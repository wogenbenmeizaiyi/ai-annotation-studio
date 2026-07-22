import logging

import uvicorn
from fastapi import FastAPI, Request

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
)
logger = logging.getLogger(__name__)

app = FastAPI(title="Callback Test Server")


@app.post("/callback")
async def receive_callback(request: Request) -> dict:
    body = await request.body()
    body_text = body.decode("utf-8")
    logger.info("callback received body=%s", body_text)
    return {"status": "ok"}


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=9000)
