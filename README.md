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

    # Fast-forward time 1 second.
    await forward(1)

    # More production functions or assertions
    # ...
```


## Differences between aiofastforward.FastForward and [asynctest.ClockedTestCase](https://asynctest.readthedocs.io/en/latest/asynctest.case.html#asynctest.ClockedTestCase)

There is overlap in functionality: both support fast-forwarding time in terms of loop.call_later and loop.call_at. However, there are properties that FastForward has that ClockedTestCase does not:

- FastForward is not coupled to any particular test framework. The only requirement is that the test code must be in an async function. If you wish, you can use FastForward in an [asynctest.TestCase](https://asynctest.readthedocs.io/en/latest/asynctest.case.html#asynctest.TestCase) test.
- FastForward supports fast-forwarding asyncio.sleep.
- FastForward allows fast-forwarding time in any event loop, not just the one the test code runs in.

ClockedTestCase does have an advantage over FastForward, which may be important for some uses:

- ClockedTestCase supports Python 3.4 onwards, while FastForward supports Python 3.5.0 onwards.


## Examples

### asyncio.sleep

```python
# Production code
async def sleeper(callback):
    await asyncio.sleep(2)
    callback(0)

# Test code
from unittest.mock import Mock, call
loop = asyncio.get_event_loop()
callback = Mock()

with aiofastforward.FastForward(loop) as forward:
    asyncio.ensure_future(sleeper())

    await forward(1)
    self.assertEqual(callback.mock_calls, [])
    await forward(1)
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

    await forward(1)
    self.assertEqual(callback.mock_calls, [call(0)])
    await forward(1)
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

    await forward(1)
    self.assertEqual(callback.mock_calls, [call(0)])
    await forward(1)
    self.assertEqual(callback.mock_calls, [call(0), call(1)])
```