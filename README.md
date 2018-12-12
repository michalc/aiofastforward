# aiomocktime

Provides patched versions of [loop.call_later](https://docs.python.org/3/library/asyncio-eventloop.html#asyncio.loop.call_later), [loop.call_at](https://docs.python.org/3/library/asyncio-eventloop.html#asyncio.loop.call_at), [loop.time](https://docs.python.org/3/library/asyncio-eventloop.html#asyncio.loop.time), and [asyncio.sleep](https://docs.python.org/3/library/asyncio-task.html#asyncio.sleep). These allow you to test asynchronous code synchronously.


## Usage

### loop.call_later

```python
# Production code
async def schedule_callback(loop, callback):
    loop.call_later(1, callback, 0)
    loop.call_later(2, callback, 1)

# Test code
loop = asyncio.get_running_loop()

with aiomocktime.MockedTime(loop) as mocked_time:
    callback = Mock()
    await schedule_callback(loop, callback)

    mocked_time.forward(1)
    self.assertEqual(callback.mock_calls, [call(0)])
    mocked_time.forward(1)
    self.assertEqual(callback.mock_calls, [call(0), call(1)])
```
