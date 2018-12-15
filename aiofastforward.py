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
        self._time = 0.0
        return self

    def __exit__(self, *_, **__):
        self._loop.call_at = self._original_call_at
        self._loop.call_later = self._original_call_later
        self._loop.time = self._original_time
        asyncio.sleep = self._original_sleep

    async def __call__(self, forward_seconds):
        # Allows recently created tasks to run and schedule a sleep
        await self._original_sleep(0)

        target_time = self._time + forward_seconds
        while self._queue.queue and self._queue.queue[0].when <= target_time:
            callback = self._queue.get()
            self._time = callback.when
            callback()

            # Allows the callback to add more to the queue before this loop ends
            await self._original_sleep(0)

        self._time = target_time

    def _mocked_call_later(self, delay, callback, *args, context=None):
        when = self._time + delay
        return self._mocked_call_at(when, callback, *args, context=context)

    def _mocked_call_at(self, when, callback, *args, context=None):
        callback = TimedCallback(when, callback, args, context)
        self._queue.put(callback)
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
        self._mocked_call_later(delay, future.set_result, result)
        return await future


class TimedCallback():

    def __init__(self, when, callback, args, context):
        self.when = when
        self._callback = callback
        self._args = args
        self._context = context
        self._cancelled = False

    def __lt__(self, other):
        return self.when < other.when

    def __call__(self):
        def run_current_context(func, *args):
            return func(*args)

        run = \
            self._context.run if self._context is not None else \
            run_current_context

        run(self._callback, *self._args)

    def cancel(self):
        self._cancelled = True
        self._callback = lambda: None
        self._args = ()
        self._context = None

    def cancelled(self):
        return self._cancelled
