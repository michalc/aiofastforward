import asyncio
import unittest
from threading import (
    Thread,
)
from unittest import (
    TestCase,
)
from unittest.mock import (
    Mock,
    call,
    patch,
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

        loop = asyncio.get_event_loop()

        with aiofastforward.FastForward(loop) as forward:
            callback = Mock()
            loop.call_later(1, callback, 0)
            loop.call_later(1, callback, 1)

            await forward(1)
            self.assertEqual(callback.mock_calls, [call(0), call(1)])

    @async_test
    async def test_is_cumulative(self):

        loop = asyncio.get_event_loop()

        with aiofastforward.FastForward(loop) as forward:
            callback = Mock()
            loop.call_later(1, callback, 0)
            loop.call_later(2, callback, 1)

            await forward(1)
            self.assertEqual(callback.mock_calls, [call(0)])
            await forward(1)
            self.assertEqual(callback.mock_calls, [call(0), call(1)])

    @async_test
    async def test_correct_order(self):

        loop = asyncio.get_event_loop()

        with aiofastforward.FastForward(loop) as forward:
            callback = Mock()
            loop.call_later(2, callback, 0)
            loop.call_later(1, callback, 1)

            await forward(1)
            self.assertEqual(callback.mock_calls, [call(1)])
            await forward(1)
            self.assertEqual(callback.mock_calls, [call(1), call(0)])

    @async_test
    async def test_can_be_cancelled(self):

        loop = asyncio.get_event_loop()

        with aiofastforward.FastForward(loop) as forward:
            callback = Mock()
            handle = loop.call_later(1, callback, 0)

            self.assertEqual(handle.cancelled(), False)
            handle.cancel()
            self.assertEqual(handle.cancelled(), True)

            await forward(1)
            self.assertEqual(callback.mock_calls, [])

    @async_test
    async def test_original_restored_on_exception(self):

        loop = asyncio.get_event_loop()
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

        loop = asyncio.get_event_loop()

        with aiofastforward.FastForward(loop) as forward:
            callback = Mock()
            now = loop.time()
            loop.call_at(now + 1, callback, 0)
            loop.call_at(now + 1, callback, 1)

            await forward(1)
            self.assertEqual(callback.mock_calls, [call(0), call(1)])

    @async_test
    async def test_is_cumulative(self):

        loop = asyncio.get_event_loop()

        with aiofastforward.FastForward(loop) as forward:
            callback = Mock()
            now = loop.time()
            loop.call_at(now + 1, callback, 0)
            loop.call_at(now + 2, callback, 1)

            await forward(1)
            self.assertEqual(callback.mock_calls, [call(0)])
            await forward(1)
            self.assertEqual(callback.mock_calls, [call(0), call(1)])

    @async_test
    async def test_short_forward_not_trigger_callback(self):

        loop = asyncio.get_event_loop()

        with aiofastforward.FastForward(loop) as forward:
            callback = Mock()
            now = loop.time()
            loop.call_at(now + 2, callback, 0)

            await forward(1)
            self.assertEqual(callback.mock_calls, [])
            await forward(1)
            self.assertEqual(callback.mock_calls, [call(0)])

    @async_test
    async def test_original_restored_on_exception(self):

        loop = asyncio.get_event_loop()
        original_call_at = loop.call_at
        try:
            with aiofastforward.FastForward(loop):
                raise Exception()
        except BaseException:
            pass

        self.assertEqual(loop.call_at, original_call_at)


class TestTime(TestCase):

    @async_test
    async def test_time_is_float(self):

        loop = asyncio.get_event_loop()

        with aiofastforward.FastForward(loop) as forward:
            self.assertTrue(isinstance(loop.time(), float))
            await forward(1)
            self.assertTrue(isinstance(loop.time(), float))

    @async_test
    async def test_forward_moves_time_forward(self):

        loop = asyncio.get_event_loop()

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

        loop = asyncio.get_event_loop()
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

        loop = asyncio.get_event_loop()
        callback = Mock()

        async def sleeper():
            callback(0)
            await asyncio.sleep(1)
            callback(1)
            await asyncio.sleep(2)
            callback(2)

        with aiofastforward.FastForward(loop) as forward:

            asyncio.ensure_future(sleeper())

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

        loop = asyncio.get_event_loop()
        callback = Mock()
        event = asyncio.Event()

        async def sleeper():
            await event.wait()
            await asyncio.sleep(1)
            callback(0)

        with aiofastforward.FastForward(loop) as forward:
            callback = Mock()
            asyncio.ensure_future(sleeper())

            event.set()
            await forward(0)
            self.assertEqual(callback.mock_calls, [])

            await forward(1)
            self.assertEqual(callback.mock_calls, [call(0)])

    @async_test
    async def test_one_call_can_resolve_multiple_sleeps(self):

        loop = asyncio.get_event_loop()
        callback = Mock()

        async def sleeper():
            await asyncio.sleep(1)
            await asyncio.sleep(2)
            callback(0)

        with aiofastforward.FastForward(loop) as forward:
            asyncio.ensure_future(sleeper())

            await forward(3)
            self.assertEqual(callback.mock_calls, [call(0)])

    @async_test
    async def test_cancellation(self):

        loop = asyncio.get_event_loop()

        cancelled = False
        async def sleeper():
            nonlocal cancelled
            try:
                await asyncio.sleep(1)
            except asyncio.CancelledError:
                cancelled = True

        with aiofastforward.FastForward(loop) as forward:
            task = asyncio.ensure_future(sleeper())

            await forward(0)
            task.cancel()
            await forward(1)

            self.assertEqual(cancelled, True)

    @async_test
    async def test_multiple_calls_can_resolve_multiple_sleeps(self):

        loop = asyncio.get_event_loop()
        callback = Mock()

        async def sleeper():
            await asyncio.sleep(3)
            await asyncio.sleep(1)
            callback(0)

        with aiofastforward.FastForward(loop) as forward:
            asyncio.ensure_future(sleeper())

            await forward(2)
            self.assertEqual(callback.mock_calls, [])
            await forward(2)
            self.assertEqual(callback.mock_calls, [call(0)])

    @async_test
    async def test_returns_result(self):

        loop = asyncio.get_event_loop()
        callback = Mock()

        async def sleeper():
            value = await asyncio.sleep(1, result='value')
            callback(value)

        with aiofastforward.FastForward(loop) as forward:
            asyncio.ensure_future(sleeper())

            await forward(1)
            self.assertEqual(callback.mock_calls, [call('value')])

    @async_test
    async def test_original_restored_on_exception(self):

        loop = asyncio.get_event_loop()
        original_sleep = asyncio.sleep
        try:
            with aiofastforward.FastForward(loop):
                raise Exception()
        except BaseException:
            pass

        self.assertEqual(asyncio.sleep, original_sleep)

    @async_test
    async def test_only_patches_specified_loop(self):

        loop = asyncio.get_event_loop()

        sleep_call = None
        async def dummy_sleep(_sleep_call, result=None):
            nonlocal sleep_call
            sleep_call = _sleep_call

        original_sleep = asyncio.sleep
        asyncio.sleep = dummy_sleep

        def run_sleep():
            other_loop = asyncio.new_event_loop()
            asyncio.set_event_loop(other_loop)
            other_loop.run_until_complete(asyncio.sleep(1))

        try:
            with aiofastforward.FastForward(loop) as forward:
                thread = Thread(target=run_sleep)
                thread.start()

                # This does block the event loop in the test, but briefly
                thread.join()

                self.assertEqual(sleep_call, 1)
        finally:
            asyncio.sleep = original_sleep


# contextvars introduced in Python 3.7
try:
    import contextvars
except ImportError:
    contextvars = None

if contextvars:
    context_var = contextvars.ContextVar('var')

    class TestCallLaterContext(TestCase):

        @async_test
        async def test_if_context_not_passed_current_context_used(self):

            loop = asyncio.get_event_loop()

            context_var_callback_value = None
            def callback():
                nonlocal context_var_callback_value
                context_var_callback_value = context_var.get()
                context_var.set('callback-value')

            with aiofastforward.FastForward(loop) as forward:
                context_var.set('initial-value')
                loop.call_later(1, callback)

                await forward(1)

                self.assertEqual(context_var_callback_value, 'initial-value')
                self.assertEqual(context_var.get(), 'callback-value')

        @async_test
        async def test_if_context_passed_is_used(self):

            loop = asyncio.get_event_loop()

            context_var_callback_value = None
            def callback():
                nonlocal context_var_callback_value
                context_var_callback_value = context_var.get()
                context_var.set('callback-value')

            with aiofastforward.FastForward(loop) as forward:
                context_var.set('initial-value')
                loop.call_later(1, callback, context=contextvars.copy_context())

                await forward(1)

                self.assertEqual(context_var_callback_value, 'initial-value')
                self.assertEqual(context_var.get(), 'initial-value')


    class TestCallAtContext(TestCase):

        @async_test
        async def test_if_context_not_passed_current_context_used(self):

            loop = asyncio.get_event_loop()

            context_var_callback_value = None
            def callback():
                nonlocal context_var_callback_value
                context_var_callback_value = context_var.get()
                context_var.set('callback-value')

            with aiofastforward.FastForward(loop) as forward:
                context_var.set('initial-value')
                now = loop.time()
                loop.call_at(now + 1, callback)

                await forward(1)

                self.assertEqual(context_var_callback_value, 'initial-value')
                self.assertEqual(context_var.get(), 'callback-value')

        @async_test
        async def test_if_context_passed_is_used(self):

            loop = asyncio.get_event_loop()

            context_var_callback_value = None
            def callback():
                nonlocal context_var_callback_value
                context_var_callback_value = context_var.get()
                context_var.set('callback-value')

            with aiofastforward.FastForward(loop) as forward:
                context_var.set('initial-value')
                now = loop.time()
                loop.call_at(now + 1, callback, context=contextvars.copy_context())

                await forward(1)

                self.assertEqual(context_var_callback_value, 'initial-value')
                self.assertEqual(context_var.get(), 'initial-value')
