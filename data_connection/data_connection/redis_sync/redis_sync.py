"""Основной класс синхронизации с Redis."""

import asyncio
from collections.abc import Awaitable, Callable
from ipaddress import IPv4Address
from typing import Any, TypeAlias
from uuid import UUID

import async_state_machine as sm
from loguru import logger
from pydantic import BaseModel, Field
from redis.asyncio import Redis
from redis.exceptions import ConnectionError

from .const import HASH_NAME, WRITE_PRIORITY_DELAY
from ..datapoints import (
    datapoints_collection,
    TDatapointsCollection,
    parse_datapoint_json,
    DatapointBase,
)

_TMessage: TypeAlias = "dict[str, str] | None"


class RedisMessage(BaseModel):
    """Сообщение, полученное по подписке из Redis."""

    data: str  # noqa
    channel: str
    type_: str = Field(alias="type")
    pattern: str | None


class States(sm.StatesEnum):
    """Состояния при синхронизации."""

    disconnected = sm.enum_auto()
    init = sm.enum_auto()
    hget = sm.enum_auto()
    sub = sm.enum_auto()
    hset_pub = sm.enum_auto()


def _connection_error(
    func: Callable[["RedisSync"], Awaitable[None]],
) -> Callable[["RedisSync"], Awaitable[None]]:
    """Декоратор для ошибки подключения к redis."""

    async def decorated(self: "RedisSync") -> None:
        try:
            await func(self)
        except ConnectionError as exc:
            logger.error(exc)
            raise sm.NewStateException(States.disconnected)

    return decorated


class RedisSync:
    """Синхронизация DP через Redis."""

    def __init__(
        self,
        host: IPv4Address,
        port: int = 6379,
        datapoints_call: TDatapointsCollection | None = None,
    ) -> None:
        """Основной класс синхронизации datapoint."""
        self.__host = host
        self.__port = port

        self.__sm = sm.StateMachine(
            states=[
                sm.State(
                    name=States.disconnected,
                    on_run=[self.__state_disconnected],
                ),
                sm.State(
                    name=States.init,
                    on_run=[self.__state_init],
                ),
                sm.State(
                    name=States.hget,
                    on_run=[self.__state_hget],
                ),
                sm.State(
                    name=States.sub,
                    on_run=[self.__state_subs],
                ),
                sm.State(
                    name=States.hset_pub,
                    on_run=[self.__state_hset_pub],
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
        self.__dp_local = datapoints_call or datapoints_collection

    async def run(self):
        await self.__sm.run()

    @property
    def _not_receive_from_redis(self) -> set[UUID]:
        return self.__dp_local.keys() - self.__dp_redis.keys()

    @property
    def __not_send_to_redis(self) -> set[UUID]:
        not_synced_keys: set[UUID] = set()
        for key, dp_local in self.__dp_local.items():
            # добавляем, если DP не сихронизировался
            if key not in self.__dp_redis.keys():
                not_synced_keys.add(key)
                continue
            dp_redis = self.__dp_redis[key]
            # проверяем метки времени
            ts_changed = (
                dp_local.ts_write > dp_redis.ts_write
                or dp_local.ts_read > dp_redis.ts_read
            )
            if ts_changed:
                not_synced_keys.add(key)
        return not_synced_keys

    async def __state_disconnected(self):
        await asyncio.sleep(1)
        raise sm.NewStateException(States.init)

    @_connection_error
    async def __state_init(self) -> None:
        """Инициализация соединения."""
        self.__subs = self.__client.pubsub()  # pyright: ignore
        await self.__subs.subscribe(HASH_NAME)  # pyright: ignore
        raise sm.NewStateException(States.hget)

    @_connection_error
    async def __state_hget(self) -> None:
        """При первом запуске считываем значения."""
        not_synced_keys = self._not_receive_from_redis
        for key in not_synced_keys:
            json = await self.__client.hget(HASH_NAME, str(key))
            if json is None:
                continue
            dp = parse_datapoint_json(json)
            logger.debug("HGET, {0}".format(dp))
            self.__dp_redis[key] = dp
            _copy_from_redis_to_local(
                dp_local=self.__dp_local[key],
                dp_redis=self.__dp_redis[key],
            )
        raise sm.NewStateException(States.sub)

    @_connection_error
    async def __state_subs(self) -> None:
        """Проверям новые значения по подписке."""
        while True:
            message: _TMessage = (  # pyright: ignore
                await self.__subs.get_message(  # pyright: ignore
                    ignore_subscribe_messages=True,
                )
            )
            if message is None:
                raise sm.NewStateException(States.hset_pub)
            message_parsed = RedisMessage.parse_obj(message)
            logger.debug("SUB, {0}".format(message_parsed))
            dp = parse_datapoint_json(message_parsed.data)
            self.__dp_redis[dp.uuid] = dp
            _copy_from_redis_to_local(
                dp_local=self.__dp_local[dp.uuid],
                dp_redis=self.__dp_redis[dp.uuid],
            )

    @_connection_error
    async def __state_hset_pub(self) -> None:
        """Отправка измененных значений."""
        not_synced_keys: set[UUID] = self.__not_send_to_redis
        for key in not_synced_keys:
            need_to_send = _check_need_to_send(
                dp_local=self.__dp_local[key],
                dp_redis=self.__dp_redis.get(key, None),
            )
            if not need_to_send:
                continue
            dp_local = self.__dp_local[key]
            json = dp_local.to_json()
            await self.__client.hset(HASH_NAME, str(key), json)
            await self.__client.publish(HASH_NAME, json)
            self.__dp_redis[key] = dp_local.copy()
            logger.debug("hset, {0}".format(json))
        raise sm.NewStateException(States.hget)


def _copy_from_redis_to_local(
    dp_local: DatapointBase[Any],
    dp_redis: DatapointBase[Any],
) -> None:
    """Обновляем локальные данные, если из redis пришли более новые."""
    if dp_local.ts_write > dp_redis.ts_write + WRITE_PRIORITY_DELAY:
        return
    if dp_local.ts_read < dp_redis.ts_read:
        dp_local.set_reader(dp_redis.value_read, dp_redis.ts_read)
    if dp_local.ts_write < dp_redis.ts_write:
        dp_local.set_writer(dp_redis.value_write, dp_redis.ts_write)


def _check_need_to_send(
    dp_local: DatapointBase[Any],
    dp_redis: DatapointBase[Any] | None,
) -> bool:
    """Проверяем, нужно ли отправлять локальные данные в redis."""
    if dp_redis is None:
        return True
    if dp_local.ts_read + WRITE_PRIORITY_DELAY < dp_redis.ts_write:
        return False
    if dp_local.ts_read > dp_redis.ts_read:
        return True
    if dp_local.ts_write > dp_redis.ts_write:
        return True
    return True
