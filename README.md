# aiofastforward [![CircleCI](https://circleci.com/gh/michalc/aiofastforward.svg?style=svg)](https://circleci.com/gh/michalc/aiofastforward) [![Maintainability](https://api.codeclimate.com/v1/badges/45d56d9e0d1d408f0fd8/maintainability)](https://codeclimate.com/github/michalc/aiofastforward/maintainability) [![Test Coverage](https://api.codeclimate.com/v1/badges/45d56d9e0d1d408f0fd8/test_coverage)](https://codeclimate.com/github/michalc/aiofastforward/test_coverage)

Fast-forward time in asyncio Python by patching [loop.call_later](https://docs.python.org/3/library/asyncio-eventloop.html#asyncio.loop.call_later), [loop.call_at](https://docs.python.org/3/library/asyncio-eventloop.html#asyncio.loop.call_at), [loop.time](https://docs.python.org/3/library/asyncio-eventloop.html#asyncio.loop.time), and [asyncio.sleep](https://docs.python.org/3/library/asyncio-task.html#asyncio.sleep). This allows you to test asynchronous code synchronously.

Inspired by [AngularJS $timeout.$flush](https://docs.angularjs.org/api/ngMock/service/$timeout#flush).


## Installation

```bash
pip install aiofastforward
```


## Usage

Patching is done through a context manager, similar to [unittest.patch](https://docs.python.org/3/library/unittest.mock.html#unittest.mock.patch).

```python
import asyncio
from aiofastforward import FastForward

loop = asyncio.get_event_loop()
with FastForward(loop) as forward:
    # Call production function(s), that call asyncio.sleep, loop.call_later,
    # loop.call_at, or loop.time
    # ...

    # Fast-forward time 1 second
    # asyncio.sleeps, and loop.call_at and loop.call_later callbacks
    # will be called: as though 1 second of real-world time has passed
    await forward(1)

    # More production functions or assertions
    # ...
```

## Examples

### asyncio.sleep

```python
# Production code
async def sleeper(callback):
    await asyncio.sleep(1)
    callback(0)
    await asyncio.sleep(2)

# Test code
from unittest.mock import Mock, call
loop = asyncio.get_event_loop()
callback = Mock()

with aiofastforward.FastForward(loop) as forward:
    asyncio.ensure_future(sleeper())

    await forward(1)  # Move time forward one second
    self.assertEqual(callback.mock_calls, [])
    await forward(1)  # Move time forward another second
    self.assertEqual(callback.mock_calls, [call(0)])
```

### loop.call_later

```python
# Production code
async def schedule_callback(loop, callback):
    loop.call_later(1, callback, 0)
    loop.call_later(2, callback, 1)

# Test code
from unittest.mock import Mock, call
loop = asyncio.get_event_loop()

with aiofastforward.FastForward(loop) as forward:
    callback = Mock()
    await schedule_callback(loop, callback)

    await forward(1)  # Move time forward one second
    self.assertEqual(callback.mock_calls, [call(0)])
    await forward(1)  # Move time forward another second
    self.assertEqual(callback.mock_calls, [call(0), call(1)])
```

### loop.call_at

```python
# Production code
async def schedule_callback(loop, callback):
    now = loop.time()
    loop.call_at(now + 1, callback, 0)
    loop.call_at(now + 2, callback, 1)

# Test code
from unittest.mock import Mock, call
loop = asyncio.get_event_loop()

with aiofastforward.FastForward(loop) as forward:
    callback = Mock()
    await schedule_callback(loop, callback)

    await forward(1)  # Move time forward one second
    self.assertEqual(callback.mock_calls, [call(0)])
    await forward(1)  # Move time forward another second
    self.assertEqual(callback.mock_calls, [call(0), call(1)])
```


## `forward`ing time can block

`await forward(a)` only moves time forward, i.e. resolve calls to `asyncio.sleep` or calls the callbacks of `call_at` or `call_later`, once there are sufficient such calls that time could have progressed that amount. Calls to IO functions, even if they take non-zero amounts of real time in the test, do not advance the patched "pseudo-timeline": they are treated as instantanous.

This means that there are cases where `await forward(a)` will block forever.


```python
# Production code
async def sleeper():
    await asyncio.sleep(1)

# Test code
loop = asyncio.get_event_loop()

with aiofastforward.FastForward(loop) as forward:
    asyncio.ensure_future(sleeper())

    await forward(2)  # Will block forever
```

To avoid this, ensure you only `await forward` an amount less than or equal to how much pseudo-time that will be progressed by `asyncio.sleep`, `call_at` or `call_later`.

```python
# Production code
async def sleeper(callback):
    await asyncio.sleep(1)
    callback(0)
    await asyncio.sleep(1)
    callback(1)

# Test code
from unittest.mock import Mock, call
loop = asyncio.get_event_loop()

with aiofastforward.FastForward(loop) as forward:
    asyncio.ensure_future(sleeper(callback))
    start_time = loop.time()

    await forward(1.5)  # The second sleep will have been called, but not resolved
    self.assertEqual(loop.time(), start_time + 1.5)
    self.assertEqual(callback.mock_calls, [call(0)])
```

The justification for this design are the consequences of the the alternative: if it _wouldn't_ block. This would mean that all sleeps and callbacks would have to be registered _before_ the call to `forward`, and this in turn would lead to less flexible test code.

For example, the production code may have a chain of 10 `asyncio.sleep(1)`, and in the test you would like to `await forward(10)` to assert on the state of the system after these. At the time of calling `await forward(10)` however, at most one of the  `asyncio.sleep(1)` would have been called. Not blocking would mean that after `await forward(10)`, the pseudo-timeline in the world of the patched production code would not have moved forward ten seconds.


## Differences between aiofastforward.FastForward and [asynctest.ClockedTestCase](https://asynctest.readthedocs.io/en/latest/asynctest.case.html#asynctest.ClockedTestCase)

There is overlap in functionality: both support fast-forwarding time in terms of loop.call_later and loop.call_at. However, there are properties that FastForward has that ClockedTestCase does not:

- FastForward is not coupled to any particular test framework. The only requirement is that the test code must be in an async function. If you wish, you can use FastForward in an [asynctest.TestCase](https://asynctest.readthedocs.io/en/latest/asynctest.case.html#asynctest.TestCase) test.
- FastForward supports fast-forwarding asyncio.sleep.
- FastForward allows fast-forwarding time in any event loop, not just the one the test code runs in.

ClockedTestCase does have an advantage over FastForward, which may be important for some uses:

- ClockedTestCase supports Python 3.4 onwards, while FastForward supports Python 3.5.0 onwards.
