from __future__ import annotations

import os
from datetime import datetime
from typing import Optional, Literal
from pydantic import BaseModel, Field

import logging

import json
from fastapi import FastAPI, status, Response, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware

from fcmNotificationSender import FCMAsyncSender
from sheetsRepository import SheetsRepository
from changesDetector import ChangesDetector

from firebase_admin import credentials, initialize_app

# Finish imports

# App start timestamp
start_time: datetime = datetime.now()

# Create logger
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger(__name__)
logger.info(f"[main] Service started at {start_time}")

# Connect to storage (Google sheet)
logger.info(f"[main] Connecting to google storage")

data_handler = SheetsRepository(
    spreadsheet_id_env_key="GOOGLE_SHEETS_SPREADSHEET_ID",
    credentials_path="credentials.json"
)
logger.info(f"[main] Connected to google storage")

logger.info(f"[main] Start downloading saved data")
changes_detector = ChangesDetector(data_handler)
changes_detector.populate()
logger.info(f"[main] End downloading saved data")

logger.info(f"[main] Start FCMAsyncSender")
sender = FCMAsyncSender(
    fixed_title="Schedule changed!",
    fixed_body="Schedule for your watched queue has changed! Make sure to check the updated schedule! ",
)
logger.info(f"[main] FCMAsyncSender started successfully")

logger.info(f"[main] Service is up and running")

# Start App
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize FCAsync Sender on startup

@app.on_event("startup")
async def startup():
    if os.getenv("FIREBASE_SERVICE_ACCOUNT"):
        # Running on Render / production
        service_account_info = json.loads(
            os.getenv("FIREBASE_SERVICE_ACCOUNT")
        )
        cred = credentials.Certificate(service_account_info)
    else:
        # Local dev
        cred = credentials.Certificate("service_account.json")
    initialize_app(cred)
    await sender.start()


@app.on_event("shutdown")
async def shutdown():
    await sender.stop()


# Default GETs
@app.get("/")
async def root():
    logger.info(f"[root] response: \"Running since {start_time}\"")
    return {"message": f"Running since {start_time}"}


@app.get("/devices")
def devices():
    items_list = data_handler.list_devices()
    json_string: str = json.dumps(items_list, indent=2)
    logger.info(f"[devices] response: \"{json_string}\"")
    return Response(content=json_string, media_type="application/json")


@app.get("/intervals")
def intervals():
    items_list = data_handler.list_intervals()
    json_string: str = json.dumps(items_list, indent=2)
    logger.info(f"[intervals] response: \"{json_string}\"")
    return Response(content=json_string, media_type="application/json")


# This is where it becomes interesting

# RegisterDevice

class RegisterDeviceRequest(BaseModel):
    device_uuid: str = Field(..., min_length=1)
    device_type: Literal["IOS", "ANDROID", "WEB"] = Field(..., min_length=1)
    push_address: str = Field(..., min_length=1)
    watched_queue: Literal["1/1", "1/2", "2/1", "2/2", "3/1", "3/2", "4/1", "4/2", "5/1", "5/2", "6/1", "6/2",] = Field(
        ..., min_length=1)
    device_details: Optional[str] = None


@app.post("/registerDevice")
async def register_device(body: RegisterDeviceRequest):
    logger.info(f"[registerDevice] request: \"{body}\"")
    data_handler.save_device(**body.model_dump())
    changes_detector.repopulate_devices()
    return {"message": "Device saved"}


# Worker request (should be triggered externally every N minutes)

@app.get("/checkChanges")
async def check_changes(bg: BackgroundTasks):
    logger.info("[checkChanges] Triggered")
    results = changes_detector.seek_changes()
    logger.info("[checkChanges] Check devices for changed queues")
    queued_notifications = 0
    for queue in results[0]:
        logger.info(f"[checkChanges] Devices for queue {queue}")
        for device in changes_detector.devices_list:
            if device["watched_queue"] == queue:
                bg.add_task(sender.enqueue_token, device["push_address"])
                logger.info(f"[checkChanges] Queued notification for {device['device_type']} {device['device_uuid']}")
                queued_notifications += 1
    logger.info(f"[checkChanges] Queued notifications for {queued_notifications} devicess")
    return {"result": "Success", "detected_changes": results[0], "pushes_scheduled": queued_notifications}
