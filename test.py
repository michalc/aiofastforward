import asyncio
import unittest
from unittest import (
    TestCase,
)
from unittest.mock import (
    Mock,
    call,
)

import aiomocktime


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

        with aiomocktime.MockedTime(loop) as mocked_time:
            callback = Mock()
            loop.call_later(1, callback, 0)
            loop.call_later(1, callback, 1)

            mocked_time.forward(1)
            self.assertEqual(callback.mock_calls, [call(0), call(1)])

    @async_test
    async def test_is_cumulative(self):

        loop = asyncio.get_running_loop()

        with aiomocktime.MockedTime(loop) as mocked_time:
            callback = Mock()
            loop.call_later(1, callback, 0)
            loop.call_later(2, callback, 1)

            mocked_time.forward(1)
            self.assertEqual(callback.mock_calls, [call(0)])
            mocked_time.forward(1)
            self.assertEqual(callback.mock_calls, [call(0), call(1)])

    @async_test
    async def test_original_restored_on_exception(self):

        loop = asyncio.get_running_loop()
        original_call_later = loop.call_later
        try:
            with aiomocktime.MockedTime(loop):
                raise Exception()
        except BaseException:
            pass

        self.assertEqual(loop.call_later, original_call_later)


class TestCallAt(TestCase):

    @async_test
    async def test_concurrent_called_in_order(self):

        loop = asyncio.get_running_loop()

        with aiomocktime.MockedTime(loop) as mocked_time:
            callback = Mock()
            loop.call_at(1, callback, 0)
            loop.call_at(1, callback, 1)

            mocked_time.forward(1)
            self.assertEqual(callback.mock_calls, [call(0), call(1)])

    @async_test
    async def test_is_cumulative(self):

        loop = asyncio.get_running_loop()

        with aiomocktime.MockedTime(loop) as mocked_time:
            callback = Mock()
            loop.call_at(1, callback, 0)
            loop.call_at(2, callback, 1)

            mocked_time.forward(1)
            self.assertEqual(callback.mock_calls, [call(0)])
            mocked_time.forward(1)
            self.assertEqual(callback.mock_calls, [call(0), call(1)])

    @async_test
    async def test_short_forward_not_trigger_callback(self):

        loop = asyncio.get_running_loop()

        with aiomocktime.MockedTime(loop) as mocked_time:
            callback = Mock()
            loop.call_at(2, callback, 0)

            mocked_time.forward(1)
            self.assertEqual(callback.mock_calls, [])
            mocked_time.forward(1)
            self.assertEqual(callback.mock_calls, [call(0)])

    @async_test
    async def test_original_restored_on_exception(self):

        loop = asyncio.get_running_loop()
        original_call_at = loop.call_at
        try:
            with aiomocktime.MockedTime(loop):
                raise Exception()
        except BaseException:
            pass

        self.assertEqual(loop.call_at, original_call_at)


class TestTime(TestCase):

    @async_test
    async def test_forward_moves_time_forward(self):

        loop = asyncio.get_running_loop()

        with aiomocktime.MockedTime(loop) as mocked_time:
            time_a = loop.time()
            mocked_time.forward(1)
            time_b = loop.time()
            mocked_time.forward(2)
            time_c = loop.time()

            self.assertEqual(time_b, time_a + 1)
            self.assertEqual(time_c, time_b + 2)

    @async_test
    async def test_original_restored_on_exception(self):

        loop = asyncio.get_running_loop()
        original_time = loop.time
        try:
            with aiomocktime.MockedTime(loop):
                raise Exception()
        except BaseException:
            pass

        self.assertEqual(loop.time, original_time)
