import asyncio
from typing import Optional

from firebase_admin import messaging


class FCMAsyncSender:
    def __init__(self, fixed_title: str, fixed_body: str):
        self.queue: asyncio.Queue[str] = asyncio.Queue()
        self.fixed_title = fixed_title
        self.fixed_body = fixed_body
        self._task: Optional[asyncio.Task] = None

    async def start(self):
        self._task = asyncio.create_task(self._worker())

    async def stop(self):
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass

    async def enqueue_token(self, token: str):
        await self.queue.put(token)

    async def _worker(self):
        while True:
            token = await self.queue.get()
            await self._send_fcm(token)
            self.queue.task_done()

    async def _send_fcm(self, token: str):
        message = messaging.Message(
            token=token,
            notification=messaging.Notification(
                title=self.fixed_title,
                body=self.fixed_body,
            ),
        )

        await asyncio.to_thread(messaging.send, message)
