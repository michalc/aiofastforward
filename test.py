import asyncio
import unittest
from threading import (
    Thread,
)
from unittest.mock import (
    Mock,
    call,
    patch,
)

import aiofastforward


async def test_call_later_concurrent_called_in_order():

    loop = asyncio.get_event_loop()

    with aiofastforward.FastForward(loop) as forward:
        callback = Mock()
        loop.call_later(1, callback, 0)
        loop.call_later(1, callback, 1)

        forward(1)
        assert callback.mock_calls == [call(0), call(1)]


async def test_call_later_is_cumulative_no_await():

    loop = asyncio.get_event_loop()

    with aiofastforward.FastForward(loop) as forward:
        callback = Mock()
        loop.call_later(1, callback, 0)
        loop.call_later(2, callback, 1)

        forward(1)
        callback.mock_calls == [call(0)]
        forward(1)
        assert callback.mock_calls == [call(0), call(1)]


async def test_call_later_is_cumulative_with_await():

    loop = asyncio.get_event_loop()

    with aiofastforward.FastForward(loop) as forward:
        callback = Mock()
        loop.call_later(1, callback, 0)
        loop.call_later(2, callback, 1)

        await forward(1)
        callback.mock_calls == [call(0)]
        await forward(1)
        callback.mock_call == [call(0), call(1)]


async def test_call_later_correct_order():

    loop = asyncio.get_event_loop()

    with aiofastforward.FastForward(loop) as forward:
        callback = Mock()
        loop.call_later(2, callback, 0)
        loop.call_later(1, callback, 1)

        forward(1)
        assert callback.mock_calls == [call(1)]
        forward(1)
        assert callback.mock_calls == [call(1), call(0)]


async def test_call_later_zero_correct_order():

    loop = asyncio.get_event_loop()

    with aiofastforward.FastForward(loop) as forward:
        callback = Mock()
        loop.call_later(0, callback, 0)

        assert callback.mock_calls == []
        forward(0)
        assert callback.mock_calls == [call(0)]


async def test_call_later_callback_called_if_after_forward():

    loop = asyncio.get_event_loop()

    with aiofastforward.FastForward(loop) as forward:
        called = asyncio.Event()

        assert not called.is_set()
        forward(1)
        loop.call_later(1, called.set)
        await called.wait()


async def test_call_later_can_be_cancelled():

    loop = asyncio.get_event_loop()

    with aiofastforward.FastForward(loop) as forward:
        callback = Mock()
        handle = loop.call_later(1, callback, 0)

        assert not handle._cancelled
        handle.cancel()
        assert handle._cancelled

        await forward(1)
        assert callback.mock_calls == []


async def test_call_later_handle_is_timerhandle():

    loop = asyncio.get_event_loop()

    with aiofastforward.FastForward(loop) as forward:
        callback = Mock()
        handle = loop.call_later(1, callback, 0)
        assert isinstance(handle, asyncio.TimerHandle)


async def test_call_later_original_restored_on_exception():

    loop = asyncio.get_event_loop()
    original_call_later = loop.call_later
    try:
        with aiofastforward.FastForward(loop):
            raise Exception()
    except BaseException:
        pass

    assert loop.call_later == original_call_later


async def test_call_at_concurrent_called_in_order():

    loop = asyncio.get_event_loop()

    with aiofastforward.FastForward(loop) as forward:
        callback = Mock()
        now = loop.time()
        loop.call_at(now + 1, callback, 0)
        loop.call_at(now + 1, callback, 1)

        forward(1)
        assert callback.mock_calls == [call(0), call(1)]

async def test_call_at_is_cumulative():

    loop = asyncio.get_event_loop()

    with aiofastforward.FastForward(loop) as forward:
        callback = Mock()
        now = loop.time()
        loop.call_at(now + 1, callback, 0)
        loop.call_at(now + 2, callback, 1)

        forward(1)
        assert callback.mock_calls == [call(0)]
        forward(1)
        assert callback.mock_calls == [call(0), call(1)]

async def test_call_at_short_forward_not_trigger_callback():

    loop = asyncio.get_event_loop()

    with aiofastforward.FastForward(loop) as forward:
        callback = Mock()
        now = loop.time()
        loop.call_at(now + 2, callback, 0)

        forward(1)
        assert callback.mock_calls == []
        forward(1)
        assert callback.mock_calls == [call(0)]

async def test_call_at_original_restored_on_exception():

    loop = asyncio.get_event_loop()
    original_call_at = loop.call_at
    try:
        with aiofastforward.FastForward(loop):
            raise Exception()
    except BaseException:
        pass

    assert loop.call_at == original_call_at


async def test_time_is_float():

    loop = asyncio.get_event_loop()

    with aiofastforward.FastForward(loop) as forward:
        assert isinstance(loop.time(), float)
        forward(1)
        assert isinstance(loop.time(), float)

async def test_time_forward_moves_time_forward_after_sleep_resolves():

    loop = asyncio.get_event_loop()

    async def sleeper_a():
        await asyncio.sleep(1)

    async def sleeper_b():
        await asyncio.sleep(2)

    with aiofastforward.FastForward(loop) as forward:
        time_a = loop.time()
        forward(1)
        time_b = loop.time()
        forward(2)
        time_c = loop.time()

        assert time_b == time_a
        assert time_c == time_a

        await asyncio.ensure_future(sleeper_a())
        assert loop.time() == 1
        await asyncio.ensure_future(sleeper_b())
        assert loop.time() == 3

async def test_time_forward_moves_time_forward_after_forward_awaited():

    loop = asyncio.get_event_loop()

    async def sleeper_a():
        await asyncio.sleep(1)

    async def sleeper_b():
        await asyncio.sleep(2)

    with aiofastforward.FastForward(loop) as forward:
        time_a = loop.time()
        forward_1 = forward(1)
        time_b = loop.time()
        forward_3 = forward(2)
        time_c = loop.time()

        assert time_b == time_a
        assert time_c == time_a

        task_a = asyncio.ensure_future(sleeper_a())
        await forward_1
        assert loop.time() == 1
        task_b = asyncio.ensure_future(sleeper_b())
        await forward_3
        assert loop.time() == 3

        task_a.cancel()
        task_b.cancel()

async def test_time_forward_moves_time_forward_after_each_await_even_if_no_exact_callback():

    loop = asyncio.get_event_loop()

    async def sleeper():
        await asyncio.sleep(3)

    with aiofastforward.FastForward(loop) as forward:
        time_a = loop.time()

        task = asyncio.ensure_future(sleeper())
        await forward(1)
        assert loop.time() == time_a + 1
        await forward(1)
        assert loop.time() == time_a + 2

        task.cancel()

async def test_time_original_restored_on_exception():

    loop = asyncio.get_event_loop()
    original_time = loop.time
    try:
        with aiofastforward.FastForward(loop):
            raise Exception()
    except BaseException:
        pass

    assert loop.time == original_time


async def test_sleep_is_cumulative():

    loop = asyncio.get_event_loop()
    at_0 = asyncio.Event()
    at_1 = asyncio.Event()
    at_3 = asyncio.Event()

    async def sleeper():
        at_0.set()
        await asyncio.sleep(1)
        at_1.set()
        await asyncio.sleep(2)
        at_3.set()

    with aiofastforward.FastForward(loop) as forward:

        task = asyncio.ensure_future(sleeper())

        forward(0)
        await at_0.wait()

        forward(0)
        assert not at_1.is_set()

        forward(1)
        await at_1.wait()

        forward(1)
        assert not at_3.is_set()

        forward(1)
        await at_3.wait()

        task.cancel()

async def test_sleep_can_resolve_after_yield():

    loop = asyncio.get_event_loop()
    at_0 = asyncio.Event()
    at_1 = asyncio.Event()

    async def sleeper():
        await at_0.wait()
        await asyncio.sleep(1)
        at_1.set()

    with aiofastforward.FastForward(loop) as forward:
        callback = Mock()
        task = asyncio.ensure_future(sleeper())

        at_0.set()
        forward(0)
        assert not at_1.is_set()

        forward(1)
        await at_1.wait()

        task.cancel()

async def test_sleep_out_of_order_forward_sleep_can_resolve_after_yield():

    loop = asyncio.get_event_loop()
    at_0 = asyncio.Event()
    at_1 = asyncio.Event()

    async def sleeper():
        await at_0.wait()
        await asyncio.sleep(1)
        at_1.set()

    with aiofastforward.FastForward(loop) as forward:
        callback = Mock()
        task = asyncio.ensure_future(sleeper())

        forward(1)
        at_0.set()
        assert not at_1.is_set()
        await at_1.wait()

        task.cancel()

async def test_sleep_awaiting_forward_blocks_until_time_in_one_call():

    loop = asyncio.get_event_loop()
    at_2 = asyncio.Event()

    async def sleeper():
        await asyncio.sleep(1)
        at_2.set()
        await asyncio.sleep(1)

    with aiofastforward.FastForward(loop) as forward:
        callback = Mock()
        asyncio.ensure_future(sleeper())

        await forward(2)
        assert at_2.is_set()

async def test_sleep_awaiting_forward_blocks_until_time_cumulative():

    loop = asyncio.get_event_loop()
    at_2 = asyncio.Event()

    async def sleeper():
        await asyncio.sleep(1)
        at_2.set()
        await asyncio.sleep(1)

    with aiofastforward.FastForward(loop) as forward:
        callback = Mock()
        task = asyncio.ensure_future(sleeper())

        await forward(0.2)
        assert not at_2.is_set()
        await forward(0.2)
        assert not at_2.is_set()
        await forward(0.2)
        assert not at_2.is_set()
        await forward(0.2)
        assert not at_2.is_set()
        await forward(0.2)
        await at_2.wait()

        task.cancel()

async def test_sleep_forward_not_blocks_until_await_and_is_cumulative():

    loop = asyncio.get_event_loop()
    at_2 = asyncio.Event()

    async def sleeper():
        await asyncio.sleep(1)
        at_2.set()
        await asyncio.sleep(1)

    with aiofastforward.FastForward(loop) as forward:
        callback = Mock()
        task = asyncio.ensure_future(sleeper())

        forward(0.2)
        assert not at_2.is_set()
        forward(0.2)
        assert not at_2.is_set()
        forward(0.2)
        assert not at_2.is_set()
        forward(0.2)
        assert not at_2.is_set()
        await forward(0.2)
        await at_2.wait()

        task.cancel()

async def test_sleep_awaiting_forward_blocks_until_time_just_after_sleep():

    loop = asyncio.get_event_loop()
    at_2 = asyncio.Event()
    at_3 = asyncio.Event()

    async def sleeper():
        await asyncio.sleep(1)
        at_2.set()
        await asyncio.sleep(1)
        at_3.set()

    with aiofastforward.FastForward(loop) as forward:
        callback = Mock()
        task = asyncio.ensure_future(sleeper())

        await forward(1.5)
        assert at_2.is_set()
        assert not at_3.is_set()
        task.cancel()

async def test_sleep_one_call_can_resolve_multiple_sleeps():

    loop = asyncio.get_event_loop()
    at_3 = asyncio.Event()

    async def sleeper():
        await asyncio.sleep(1)
        await asyncio.sleep(2)
        at_3.set()

    with aiofastforward.FastForward(loop) as forward:
        task = asyncio.ensure_future(sleeper())

        forward(3)
        await at_3.wait()

        task.cancel()

async def test_sleep_cancellation():

    loop = asyncio.get_event_loop()
    running = asyncio.Event()
    cancelled = asyncio.Event()

    async def sleeper():
        try:
            running.set()
            await asyncio.sleep(1)
        except asyncio.CancelledError:
            cancelled.set()

    with aiofastforward.FastForward(loop) as forward:
        task = asyncio.ensure_future(sleeper())

        forward(0)
        await running.wait()

        task.cancel()

        forward(1)
        await cancelled.wait()

async def test_sleep_multiple_calls_can_resolve_multiple_sleeps_no_await():

    loop = asyncio.get_event_loop()
    at_4 = asyncio.Event()

    async def sleeper():
        await asyncio.sleep(3)
        await asyncio.sleep(1)
        at_4.set()

    with aiofastforward.FastForward(loop) as forward:
        task = asyncio.ensure_future(sleeper())

        forward(2)
        assert not at_4.is_set()
        forward(2)
        await at_4.wait()

        task.cancel()

async def test_sleep_multiple_calls_can_resolve_multiple_sleeps_with_await():

    loop = asyncio.get_event_loop()
    at_4 = asyncio.Event()

    async def sleeper():
        await asyncio.sleep(3)
        await asyncio.sleep(1)
        at_4.set()

    with aiofastforward.FastForward(loop) as forward:
        task = asyncio.ensure_future(sleeper())

        await forward(2)
        assert not at_4.is_set()
        await forward(2)
        await at_4.wait()

        task.cancel()

async def test_sleep_returns_result():

    loop = asyncio.get_event_loop()
    result = asyncio.Future()

    async def sleeper():
        value = await asyncio.sleep(1, result='value')
        result.set_result(value)

    with aiofastforward.FastForward(loop) as forward:
        task = asyncio.ensure_future(sleeper())

        forward(1)
        assert await result == 'value'

        task.cancel()

async def test_sleep_original_restored_on_exception():

    loop = asyncio.get_event_loop()
    original_sleep = asyncio.sleep
    try:
        with aiofastforward.FastForward(loop):
            raise Exception()
    except BaseException:
        pass

    assert asyncio.sleep == original_sleep

async def test_sleep_only_patches_specified_loop():

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

            assert sleep_call == 1
    finally:
        asyncio.sleep = original_sleep


# contextvars introduced in Python 3.7
try:
    import contextvars
except ImportError:
    contextvars = None

if contextvars:
    context_var = contextvars.ContextVar('var')

    async def test_call_later_context_if_context_not_passed_copy_of_current_context_used():

        loop = asyncio.get_event_loop()

        context_var_callback_value = None
        def callback():
            nonlocal context_var_callback_value
            context_var_callback_value = context_var.get()
            context_var.set('callback-value')

        with aiofastforward.FastForward(loop) as forward:
            context_var.set('initial-value')
            loop.call_later(1, callback)

            forward(1)

            assert context_var_callback_value == 'initial-value'
            assert context_var.get() == 'initial-value'

    async def test_call_later_context_if_context_passed_is_used():

        loop = asyncio.get_event_loop()

        context_var_callback_value = None
        def callback():
            nonlocal context_var_callback_value
            context_var_callback_value = context_var.get()
            context_var.set('callback-value')

        with aiofastforward.FastForward(loop) as forward:
            context_var.set('initial-value')
            context = contextvars.copy_context()
            context_var.set('modified-value')
            loop.call_later(1, callback, context=context)

            forward(1)

            assert context_var_callback_value == 'initial-value'
            assert context_var.get() == 'modified-value'

    async def test_call_at_context_if_context_not_passed_copy_of_current_context_used():

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

            forward(1)

            assert context_var_callback_value == 'initial-value'
            assert context_var.get() == 'initial-value'

    async def test_call_at_context_if_context_passed_is_used():

        loop = asyncio.get_event_loop()

        context_var_callback_value = None
        def callback():
            nonlocal context_var_callback_value
            context_var_callback_value = context_var.get()
            context_var.set('callback-value')

        with aiofastforward.FastForward(loop) as forward:
            context_var.set('initial-value')
            context = contextvars.copy_context()
            context_var.set('modified-value')
            now = loop.time()
            loop.call_at(now + 1, callback, context=context)

            forward(1)

            assert context_var_callback_value == 'initial-value'
            assert context_var.get() == 'modified-value'
