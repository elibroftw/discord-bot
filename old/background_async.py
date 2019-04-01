import asyncio
import time
import concurrent.futures


def test(something):
    time.sleep(2)
    print('hey')
    time.sleep(2)
    print('hey')
    return something


def cpu_bound():
    # CPU-bound operations will block the event loop:
    # in general it is preferable to run them in a
    # process pool.
    return sum(i * i for i in range(10 ** 7))


def main():
    loop = asyncio.get_event_loop()
    result = loop.run_in_executor(None, test, 'yoo')
    print(type(result))
    data1 = yield from result
    # print(result)


if __name__ == '__main__':
    # loop = asyncio.get_event_loop()
    # loop.run_until_complete(main())
    asyncio.run(main())
    # asyncio.get_event_loop().run_until_complete(long_io_task('yooo'))
