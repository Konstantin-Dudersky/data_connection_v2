import asyncio
from ipaddress import IPv4Address
from typing import Any
from uuid import UUID

from loguru import logger
from redis.asyncio import Redis
from redis.exceptions import ConnectionError

import async_state_machine as sm

from .const import HASH_NAME, WRITE_PRIORITY_DELAY
from ..datapoints import (
    TDatapointsCollection,
    parse_datapoint_json,
    DatapointBase,
)


class States(sm.StatesEnum):
    disconnected = sm.enum_auto()
    ping = sm.enum_auto()
    hget = sm.enum_auto()
    hset = sm.enum_auto()


class RedisSync:
    def __init__(
        self,
        datapoints_collection: TDatapointsCollection,
        host: IPv4Address,
        port: int = 6379,
    ) -> None:
        """Основной класс синхронизации datapoint."""
        self.__host = host
        self.__port = port

        self.__sm = sm.StateMachine(
            states=[
                sm.State(
                    name=States.disconnected,
                    on_run=[self.state_disconnected_run],
                ),
                sm.State(
                    name=States.ping,
                    on_run=[self.state_ping_run],
                ),
                sm.State(
                    name=States.hget,
                    on_run=[self.state_hget_run],
                ),
                sm.State(
                    name=States.hset,
                    on_run=[self.state_hset_run],
                ),
            ],
            states_enum=States,
            init_state=States.disconnected,
        )
        self.__client: Redis[str] = Redis(
            host=str(self.__host),
            port=self.__port,
            decode_responses=True,
        )
        self.__dp_redis: TDatapointsCollection = {}
        self.__dp_local = datapoints_collection

    async def run(self):
        await self.__sm.run()

    async def state_disconnected_run(self):
        await asyncio.sleep(1)
        raise sm.NewStateException(States.ping)

    async def state_ping_run(self):
        try:
            await self.__client.ping()
        except ConnectionError:
            print("disconnected")
            raise sm.NewStateException(States.disconnected)
        raise sm.NewStateException(States.hget)

    async def state_hget_run(self):
        not_synced_keys = self.__dp_local.keys() - self.__dp_redis.keys()
        for key in not_synced_keys:
            json = await self.__client.hget(HASH_NAME, str(key))
            if json is None:
                continue
            dp = parse_datapoint_json(json)
            logger.debug("hget, {0}".format(dp))
            self.__dp_redis[key] = dp
            copy_redis_to_local(
                dp_local=self.__dp_local[key],
                dp_redis=self.__dp_redis[key],
            )
        raise sm.NewStateException(States.hset)

    async def state_hset_run(self):
        not_synced_keys: set[UUID] = set()
        for key, dp in self.__dp_local.items():
            # добавляем, если DP не сихронизировался
            if key not in self.__dp_redis.keys():
                not_synced_keys.add(key)
                continue
            # TODO - проверять по меткам времени
            if dp != self.__dp_redis[key]:
                not_synced_keys.add(key)
                continue
        for key in not_synced_keys:
            dp = self.__dp_local[key]
            json = dp.to_json()
            await self.__client.hset(HASH_NAME, str(key), json)
            self.__dp_redis[key] = parse_datapoint_json(json)
            logger.debug("hset, {0}".format(json))
        raise sm.NewStateException(States.ping)


def copy_redis_to_local(
    dp_local: DatapointBase[Any],
    dp_redis: DatapointBase[Any],
) -> None:
    if dp_local.ts_write > dp_redis.ts_write + WRITE_PRIORITY_DELAY:
        return
    if dp_local.ts_read < dp_redis.ts_read:
        dp_local.set_reader(dp_redis.value_read, dp_redis.ts_read)
    if dp_local.ts_write < dp_redis.ts_write:
        dp_local.set_writer(dp_redis.value_write, dp_redis.ts_write)


def copy_local_to_redis(
    dp_local: DatapointBase[Any],
    dp_redis: DatapointBase[Any],
) -> DatapointBase[Any] | None:
    need_to_send = False
    if dp_local.ts_read + WRITE_PRIORITY_DELAY < dp_redis.ts_write:
        return None
    if dp_local.ts_read > dp_redis.ts_read:
        need_to_send = True
    if dp_local.ts_write > dp_redis.ts_write:
        need_to_send = True
    if need_to_send:
        return dp_local.copy()
