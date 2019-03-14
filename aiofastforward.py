import asyncio
import queue

try:
    import contextvars

    def create_callback(when, callback, args, loop, context):
        return asyncio.TimerHandle(when, callback, args, loop, context=context)

except ImportError:
    def create_callback(when, callback, args, loop, _):
        return asyncio.TimerHandle(when, callback, args, loop)


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
        self._target_time = 0.0
        self._time = 0.0
        return self

    def __exit__(self, *_, **__):
        self._loop.call_at = self._original_call_at
        self._loop.call_later = self._original_call_later
        self._loop.time = self._original_time
        asyncio.sleep = self._original_sleep

    async def __call__(self, forward_seconds):
        self._target_time += forward_seconds
        self._run()

    def _run(self):
        while self._queue.queue and self._queue.queue[0]._when <= self._target_time:
            callback = self._queue.get()
            self._time = callback._when

            if not callback._cancelled:
                callback._run()

    def _mocked_call_later(self, delay, callback, *args, context=None):
        when = self._time + delay
        return self._mocked_call_at(when, callback, *args, context=context)

    def _mocked_call_at(self, when, callback, *args, context=None):
        callback = create_callback(when, callback, args, self._loop, context)
        self._queue.put(callback)
        self._run()
        return callback

    def _mocked_time(self):
        return self._time

    async def _maybe_mocked_sleep(self, delay, result=None):
        func = \
            self._mocked_sleep if asyncio.get_event_loop() == self._loop else \
            self._original_sleep
        return await func(delay, result)

    async def _mocked_sleep(self, delay, result):
        future = asyncio.Future()
        self._mocked_call_later(delay, _set_result_unless_cancelled, future, result)
        return await future


def _set_result_unless_cancelled(future, result):
    if not future.cancelled():
        future.set_result(result)
