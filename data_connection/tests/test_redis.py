import asyncio
import random


from tests.conftest import TestInstance


class StopTestError(Exception):
    pass


TIME_STEP = 0.1
TIMEOUT = 5.0


def test_set_reader(data: TestInstance):
    async def autoprogram():
        random_int = random.randint(-1000000, 1000000)
        time_remain = TIMEOUT
        data.dp1.set_reader(random_int)
        while time_remain > 0:
            await asyncio.sleep(TIME_STEP)
            time_remain -= TIME_STEP
            if data.dp2.value == random_int:
                break
        else:
            assert data.dp2.value == random_int
            assert data.dp2.value_read == random_int
        raise StopTestError

    async def run():
        async with asyncio.TaskGroup() as tg:
            tg.create_task(data.redis1.run())
            tg.create_task(data.redis2.run())
            tg.create_task(autoprogram())

    try:
        asyncio.run(run(), debug=True)
    except* StopTestError:
        pass
    else:
        assert False


def test_redis_set_writer(data: TestInstance):
    async def autoprogram():
        random_int = random.randint(-1000000, 1000000)
        time_remain = TIMEOUT
        data.dp2.value = random_int
        while time_remain > 0:
            await asyncio.sleep(TIME_STEP)
            time_remain -= TIME_STEP
            if data.dp2.value_write == random_int:
                break
        else:
            assert data.dp2.value_write == random_int
        raise StopTestError

    async def run():
        async with asyncio.TaskGroup() as tg:
            tg.create_task(data.redis1.run())
            tg.create_task(data.redis2.run())
            tg.create_task(autoprogram())

    try:
        asyncio.run(run(), debug=True)
    except* StopTestError:
        pass
    else:
        assert False


def test_redis_3(data: TestInstance):
    async def autoprogram():
        random_int = random.randint(-1000000, 1000000)
        time_remain = TIMEOUT
        data.dp2.value = random_int
        await asyncio.sleep(0.1)
        data.dp1.set_reader(random_int * 2)
        while time_remain > 0:
            await asyncio.sleep(TIME_STEP)
            time_remain -= TIME_STEP
            if data.dp1.value_write == random_int:
                break
        else:
            assert data.dp1.value_write == random_int
        raise StopTestError

    async def run():
        async with asyncio.TaskGroup() as tg:
            tg.create_task(data.redis1.run())
            tg.create_task(data.redis2.run())
            tg.create_task(autoprogram())

    try:
        asyncio.run(run(), debug=True)
    except* StopTestError:
        pass
    else:
        assert False
