import asyncio
import queue

try:
    from contextvars import (
        Context,
        copy_context,
    )
except ImportError:
    class Context():
        def run(self, func, *args):
            return func(*args)

    def copy_context():
        return Context()


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
        await _yield(self._loop)

        target_time = self._time + forward_seconds
        while self._queue.queue and self._queue.queue[0].when <= target_time:
            callback = self._queue.get()
            self._time = callback.when
            callback()

            # Allows the callback to add more to the queue before this loop ends
            await _yield(self._loop)

        self._time = target_time

    def _mocked_call_later(self, delay, callback, *args, context=None):
        when = self._time + delay
        return self._mocked_call_at(when, callback, *args, context=context)

    def _mocked_call_at(self, when, callback, *args, context=None):
        non_none_context = \
            context if context is not None else \
            copy_context()

        callback = MockTimerHandle(when, callback, args, non_none_context)
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
        self._mocked_call_later(delay, _set_result_unless_cancelled, future, result)
        return await future


class MockTimerHandle(asyncio.TimerHandle):

    def __init__(self, when, callback, args, context):
        self.when = when
        self._callback = callback
        self._args = args
        self._context = context
        self._cancelled = False

    def __lt__(self, other):
        return self.when < other.when

    def __call__(self):
        self._context.run(self._callback, *self._args)

    def cancel(self):
        self._cancelled = True
        self._callback = lambda: None
        self._args = ()
        self._context = Context()

    def cancelled(self):
        return self._cancelled


def _set_result_unless_cancelled(future, result):
    if not future.cancelled():
        future.set_result(result)


async def _yield(loop):
    # Python 3.5.0+compatible way of yielding to another task
    # (3.5.1 supports simpler ways, e.g. with asyncio.sleep(0))
    future = asyncio.Future()
    loop.call_soon(future.set_result, None)
    await future
