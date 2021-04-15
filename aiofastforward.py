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

        self._callbacks_queue = queue.PriorityQueue()
        self._forwards_queue = queue.PriorityQueue()
        self._target_time = 0.0
        self._time = 0.0
        return self

    def __exit__(self, *_, **__):
        self._loop.call_at = self._original_call_at
        self._loop.call_later = self._original_call_later
        self._loop.time = self._original_time
        asyncio.sleep = self._original_sleep

    def __call__(self, forward_seconds):
        self._target_time += forward_seconds
        acheived_target = asyncio.Event()
        callback = create_callback(self._target_time, acheived_target.set, (), self._loop, None)
        self._forwards_queue.put(callback)
        self._run()
        return acheived_target.wait()

    def _schedule_run(self):
        self._original_call_at(0, self._run)

    def _run(self):
        scheduled = False
        busy = False
        for task in self._loop._ready:
            if task._callback == self._run:
                scheduled = True
            else:
                busy = True
        if busy:
            if not scheduled:
                self._schedule_run()
            return

        # Resolve all forwards strictly before first callback if there is one
        while \
                self._callbacks_queue.queue and self._forwards_queue.queue \
                and self._forwards_queue.queue[0] <  self._callbacks_queue.queue[0]:
            self._progress_time(self._forwards_queue)

        # Run expired callbacks
        if self._callbacks_queue.queue and self._callbacks_queue.queue[0]._when <= self._target_time:
            # Only run the callbacks that expired at this instance, but no more -- they might schedule callbacks on their own
            t0 = self._callbacks_queue.queue[0]._when
            while self._callbacks_queue.queue and self._callbacks_queue.queue[0]._when == t0:
                self._progress_time(self._callbacks_queue)
            self._schedule_run()
        else:
            # Resolve all forwards at this callback, if no more callbacks at time
            is_last_callback_at_time = \
                not self._callbacks_queue.queue or \
                self._callbacks_queue.queue[0]._when > self._time
            if is_last_callback_at_time:
                while self._forwards_queue.queue and self._forwards_queue.queue[0]._when <= self._time:
                    self._progress_time(self._forwards_queue)

    def _progress_time(self, queue):
        callback = queue.get()
        self._time = callback._when
        if not callback._cancelled:
            callback._run()

    def _mocked_call_later(self, delay, callback, *args, context=None):
        when = self._time + delay
        return self._mocked_call_at(when, callback, *args, context=context)

    def _mocked_call_at(self, when, callback, *args, context=None):
        callback = create_callback(when, callback, args, self._loop, context)
        self._callbacks_queue.put(callback)
        self._schedule_run()
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
