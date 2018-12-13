import asyncio
import queue


class FastForward():

    def __init__(self, loop):
        self._loop = loop

    def __enter__(self):
        self._original_call_later = self._loop.call_later
        self._original_call_at = self._loop.call_at
        self._original_time = self._loop.time
        self._original_sleep = asyncio.sleep
        self._loop.call_later = self._mocked_call_later
        self._loop.call_at = self._mocked_call_at
        self._loop.time = self._mocked_time
        asyncio.sleep = self._maybe_mocked_sleep

        self._queue = queue.PriorityQueue()
        self._time = 0
        return self

    def __exit__(self, *_, **__):
        self._loop.call_at = self._original_call_at
        self._loop.call_later = self._original_call_later
        self._loop.time = self._original_time
        asyncio.sleep = self._original_sleep

    async def __call__(self, time_seconds):
        # Allows recently created tasks to run and schedule a sleep
        await self._original_sleep(0)

        target_time = self._time + time_seconds
        while self._queue.queue and self._queue.queue[0].time <= target_time:
            callback = self._queue.get()
            self._time = callback.time
            if callback.cancelled():
                continue

            callback()

            # Allows the callback to add more to the queue before this loop ends
            await self._original_sleep(0)

        self._time = target_time

    def _mocked_call_later(self, delay, callback, *args):
        time = self._time + delay
        return self._mocked_call_at(time, callback, *args)

    def _mocked_call_at(self, time, callback, *args):
        callback = TimedCallback(time, callback, args)
        self._queue.put(callback)
        return callback

    def _mocked_time(self):
        return self._time

    async def _maybe_mocked_sleep(self, delay):
        func = \
            self._mocked_sleep if asyncio.get_event_loop() == self._loop else \
            self._original_sleep
        await func(delay)

    async def _mocked_sleep(self, delay):
        event = asyncio.Event()
        self._mocked_call_later(delay, event.set)
        await event.wait()


class TimedCallback():

    def __init__(self, time, callback, args):
        self.time = time
        self._callback = callback
        self._args = args
        self._cancelled = False

    def __lt__(self, other):
        return self.time < other.time

    def __call__(self):
        self._callback(*self._args)

    def cancel(self):
        self._cancelled = True

    def cancelled(self):
        return self._cancelled
