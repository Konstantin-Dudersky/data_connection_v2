import asyncio
from uuid import UUID

from copy import deepcopy
from ipaddress import IPv4Address

from data_connection.redis_sync.redis_sync import RedisSync
from data_connection.datapoints import DatapointInt, datapoints_collection


class StopTestError(Exception):
    pass


def test_redis():
    uuid = UUID("488c57c0-f54f-4cf9-8e35-62363f7b47b8")
    dp1 = DatapointInt(uuid=uuid)
    dpc1 = datapoints_collection
    dpc2 = deepcopy(datapoints_collection)
    dp2 = dpc2[uuid]
    assert id(dpc1) != id(dpc2)
    assert id(dp1) != id(dp2)

    redis1 = RedisSync(
        datapoints_collection=dpc1,
        host=IPv4Address("192.168.101.12"),
    )
    redis2 = RedisSync(
        datapoints_collection=dpc2,
        host=IPv4Address("192.168.101.12"),
    )

    async def autoprogram():
        dp1.value = 123
        await asyncio.sleep(5.0)
        print("StopTestError")
        raise StopTestError
        assert dp2.value == 123

    async def run():
        async with asyncio.TaskGroup() as tg:
            tg.create_task(redis1.run())
            tg.create_task(redis2.run())
            tg.create_task(autoprogram())

    try:
        asyncio.run(run(), debug=True)
    except* StopTestError:
        pass


def test_asyncio():
    async def fast_task_1():
        while True:
            await asyncio.sleep(0)

    async def fast_task_2():
        while True:
            await asyncio.sleep(0)

    async def slow_task():
        # while True:
        await asyncio.sleep(5)
        print("slow task")
        raise Exception

    async def main():
        async with asyncio.TaskGroup() as tg:
            tg.create_task(fast_task_1())
            tg.create_task(fast_task_2())
            tg.create_task(slow_task())

    asyncio.run(main())


# if __name__ == "__main__":
#     test_redis()
