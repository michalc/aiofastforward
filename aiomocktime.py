import asyncio
import queue


class MockedTime():

    def __init__(self, loop):
        self._loop = loop

    def __enter__(self):
        self._original_call_later = self._loop.call_later
        self._original_call_at = self._loop.call_at
        self._original_time = self._loop.time
        self._loop.call_later = self._mocked_call_later
        self._loop.call_at = self._mocked_call_at
        self._loop.time = self._mocked_time
        self._queue = queue.PriorityQueue()
        self._time = 0
        return self

    def __exit__(self, *_, **__):
        self._loop.call_at = self._original_call_at
        self._loop.call_later = self._original_call_later
        self._loop.time = self._original_time

    def forward(self, time_seconds):
        self._time += time_seconds
        while self._queue.queue and self._queue.queue[0].time <= self._time:
            timed_callback = self._queue.get()
            timed_callback.callback(*timed_callback.args)

    def _mocked_call_later(self, delay, callback, *args):
        time = self._time + delay
        self._queue.put(TimedCallback(time, callback, args))

    def _mocked_call_at(self, time, callback, *args):
        self._queue.put(TimedCallback(time, callback, args))

    def _mocked_time(self):
        return self._time


class TimedCallback():

    def __init__(self, time, callback, args):
        self.time = time
        self.callback = callback
        self.args = args

    def __lt__(self, other):
        return self.time < other.time
