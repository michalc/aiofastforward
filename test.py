import asyncio
import unittest
from unittest import (
    TestCase,
)
from unittest.mock import (
    Mock,
    call,
)

import aiofastforward


def async_test(func):
    def wrapper(*args, **kwargs):
        future = func(*args, **kwargs)
        loop = asyncio.get_event_loop()
        loop.run_until_complete(future)
    return wrapper


class TestCallLater(TestCase):

    @async_test
    async def test_concurrent_called_in_order(self):

        loop = asyncio.get_running_loop()

        with aiofastforward.FastForward(loop) as forward:
            callback = Mock()
            loop.call_later(1, callback, 0)
            loop.call_later(1, callback, 1)

            await forward(1)
            self.assertEqual(callback.mock_calls, [call(0), call(1)])

    @async_test
    async def test_is_cumulative(self):

        loop = asyncio.get_running_loop()

        with aiofastforward.FastForward(loop) as forward:
            callback = Mock()
            loop.call_later(1, callback, 0)
            loop.call_later(2, callback, 1)

            await forward(1)
            self.assertEqual(callback.mock_calls, [call(0)])
            await forward(1)
            self.assertEqual(callback.mock_calls, [call(0), call(1)])

    @async_test
    async def test_original_restored_on_exception(self):

        loop = asyncio.get_running_loop()
        original_call_later = loop.call_later
        try:
            with aiofastforward.FastForward(loop):
                raise Exception()
        except BaseException:
            pass

        self.assertEqual(loop.call_later, original_call_later)


class TestCallAt(TestCase):

    @async_test
    async def test_concurrent_called_in_order(self):

        loop = asyncio.get_running_loop()

        with aiofastforward.FastForward(loop) as forward:
            callback = Mock()
            loop.call_at(1, callback, 0)
            loop.call_at(1, callback, 1)

            await forward(1)
            self.assertEqual(callback.mock_calls, [call(0), call(1)])

    @async_test
    async def test_is_cumulative(self):

        loop = asyncio.get_running_loop()

        with aiofastforward.FastForward(loop) as forward:
            callback = Mock()
            loop.call_at(1, callback, 0)
            loop.call_at(2, callback, 1)

            await forward(1)
            self.assertEqual(callback.mock_calls, [call(0)])
            await forward(1)
            self.assertEqual(callback.mock_calls, [call(0), call(1)])

    @async_test
    async def test_short_forward_not_trigger_callback(self):

        loop = asyncio.get_running_loop()

        with aiofastforward.FastForward(loop) as forward:
            callback = Mock()
            loop.call_at(2, callback, 0)

            await forward(1)
            self.assertEqual(callback.mock_calls, [])
            await forward(1)
            self.assertEqual(callback.mock_calls, [call(0)])

    @async_test
    async def test_original_restored_on_exception(self):

        loop = asyncio.get_running_loop()
        original_call_at = loop.call_at
        try:
            with aiofastforward.FastForward(loop):
                raise Exception()
        except BaseException:
            pass

        self.assertEqual(loop.call_at, original_call_at)


class TestTime(TestCase):

    @async_test
    async def test_forward_moves_time_forward(self):

        loop = asyncio.get_running_loop()

        with aiofastforward.FastForward(loop) as forward:
            time_a = loop.time()
            await forward(1)
            time_b = loop.time()
            await forward(2)
            time_c = loop.time()

            self.assertEqual(time_b, time_a + 1)
            self.assertEqual(time_c, time_b + 2)

    @async_test
    async def test_original_restored_on_exception(self):

        loop = asyncio.get_running_loop()
        original_time = loop.time
        try:
            with aiofastforward.FastForward(loop):
                raise Exception()
        except BaseException:
            pass

        self.assertEqual(loop.time, original_time)


class TestSleep(TestCase):

    @async_test
    async def test_is_cumulative(self):

        loop = asyncio.get_running_loop()
        callback = Mock()

        async def sleeper():
            callback(0)
            await asyncio.sleep(1)
            callback(1)
            await asyncio.sleep(2)
            callback(2)

        with aiofastforward.FastForward(loop) as forward:

            asyncio.create_task(sleeper())

            await forward(0)
            self.assertEqual(callback.mock_calls, [call(0)])

            await forward(0)
            self.assertEqual(callback.mock_calls, [call(0)])

            await forward(1)
            self.assertEqual(callback.mock_calls, [call(0), call(1)])

            await forward(1)
            self.assertEqual(callback.mock_calls, [call(0), call(1)])

            await forward(1)
            self.assertEqual(callback.mock_calls, [call(0), call(1), call(2)])

    @async_test
    async def test_sleep_can_resolve_after_yield(self):

        loop = asyncio.get_running_loop()
        callback = Mock()
        event = asyncio.Event()

        async def sleeper():
            await event.wait()
            await asyncio.sleep(1)
            callback(0)

        with aiofastforward.FastForward(loop) as forward:
            callback = Mock()
            asyncio.create_task(sleeper())

            event.set()
            await forward(0)
            self.assertEqual(callback.mock_calls, [])

            await forward(1)
            self.assertEqual(callback.mock_calls, [call(0)])

    @async_test
    async def test_one_call_can_resolve_multiple_sleeps(self):

        loop = asyncio.get_running_loop()
        callback = Mock()

        async def sleeper():
            await asyncio.sleep(1)
            await asyncio.sleep(2)
            callback(0)

        with aiofastforward.FastForward(loop) as forward:
            asyncio.create_task(sleeper())

            await forward(3)
            self.assertEqual(callback.mock_calls, [call(0)])

    @async_test
    async def test_multiple_calls_can_resolve_multiple_sleeps(self):

        loop = asyncio.get_running_loop()
        callback = Mock()

        async def sleeper():
            await asyncio.sleep(3)
            await asyncio.sleep(1)
            callback(0)

        with aiofastforward.FastForward(loop) as forward:
            asyncio.create_task(sleeper())

            await forward(2)
            self.assertEqual(callback.mock_calls, [])
            await forward(2)
            self.assertEqual(callback.mock_calls, [call(0)])

    @async_test
    async def test_original_restored_on_exception(self):

        original_sleep = asyncio.sleep
        try:
            with aiofastforward.FastForward(loop):
                raise Exception()
        except BaseException:
            pass

        self.assertEqual(asyncio.sleep, original_sleep)
