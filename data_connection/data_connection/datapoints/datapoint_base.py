"""Базовый класс для данных."""

import abc
import datetime as dt
from copy import deepcopy
from enum import StrEnum
from typing import Any, Final, Generic, Literal, Self, Type, TypeAlias, TypeVar
from uuid import UUID

from loguru import logger

from pydantic import BaseModel
from pydantic.generics import GenericModel

TDatapoint = TypeVar("TDatapoint", bound=bool | float | int | str)

EXC_DUPL_KEY: Final[str] = "Ключ {0} уже есть в коллекции datapoints_collection"


class Access(StrEnum):
    """Типы доступа к полю."""

    rw = "rw"
    ro = "ro"
    wo = "wo"


class DatapointClass(BaseModel):
    class_name: str


class DatapointBaseModel(DatapointClass, GenericModel, Generic[TDatapoint]):
    uuid: UUID
    value_read: TDatapoint
    ts_read: dt.datetime
    value_write: TDatapoint
    ts_write: dt.datetime


class DatapointBase(abc.ABC, Generic[TDatapoint]):
    """Базовый класс для данных."""

    def __init__(
        self,
        uuid: str | UUID,
        default: TDatapoint | None = None,
        access: Literal["ro", "wo", "rw"] = "rw",
        add_to_collection: bool = True,
    ) -> None:
        """Базовый класс для данных.

        Parameters
        ----------
        default: TField
            Начальное значение
        access: str
            Доступ к полю:
            ro - read-only
            wo - write-only
            rw - read-write
        add_to_collection: bool
            True = Добавить в коллекцию dp_collection
        """
        self.__uuid: UUID
        self.__value_read: TDatapoint
        self.__value_write: TDatapoint
        self.__ts_read: dt.datetime
        self.__ts_write: dt.datetime
        self.__access: Access
        self.__json_model: Type[BaseModel]

        match uuid:
            case str():
                self.__uuid = UUID(uuid)
            case UUID():
                self.__uuid = uuid
        self.__value_read = type(self)._set_default_value(default)
        self.__value_write = type(self)._set_default_value(default)
        self.__ts_read = dt.datetime.min
        self.__ts_write = dt.datetime.min
        self.__access = Access(access)
        self.__json_model = DatapointBaseModel[TDatapoint]
        if add_to_collection:
            if self.__uuid in datapoints_collection:
                raise KeyError(EXC_DUPL_KEY.format(self.__uuid))
            datapoints_collection[self.__uuid] = self

    def __init_subclass__(cls) -> None:
        _datapoints_classes[cls.__name__] = cls

    def __eq__(self, other: Self) -> bool:
        return self.to_json() == other.to_json()

    def __repr__(self) -> str:
        return self.to_json()

    @property
    def value(self) -> TDatapoint:
        if self.__ts_read < self.__ts_write:
            return self.__value_write
        return self.__value_read

    @value.setter
    def value(self, value: TDatapoint) -> None:
        self.__ts_write = dt.datetime.utcnow()
        self.__value_write = value

    @property
    def value_read(self) -> TDatapoint:
        return self.__value_read

    @property
    def value_write(self) -> TDatapoint:
        return self.__value_write

    @property
    def ts(self) -> dt.datetime:
        return max(self.__ts_read, self.__ts_write)

    @property
    def ts_read(self) -> dt.datetime:
        return self.__ts_read

    @property
    def ts_write(self) -> dt.datetime:
        return self.__ts_write

    @property
    def access(self) -> Access:
        return self.__access

    @property
    def json_model(self) -> Type[BaseModel]:
        return self.__json_model

    @property
    def uuid(self) -> UUID:
        return self.__uuid

    @classmethod
    @abc.abstractmethod
    def _set_default_value(cls, value: TDatapoint | None) -> TDatapoint:
        ...

    def to_json(self) -> str:
        return self.__json_model(
            class_name=type(self).__name__,
            uuid=self.__uuid,
            ts_read=self.__ts_read,
            value_read=self.__value_read,
            ts_write=self.__ts_write,
            value_write=self.__value_write,
        ).json()

    @classmethod
    def from_json(cls: Type[Self], json: str) -> Self:
        model_data = DatapointBaseModel[TDatapoint].parse_raw(json)
        instance = cls(
            uuid=str(model_data.uuid),
            add_to_collection=False,
        )
        instance.set_reader(
            value=model_data.value_read,
            ts=model_data.ts_read,
        )
        instance.set_writer(
            value=model_data.value_write,
            ts=model_data.ts_write,
        )
        return instance

    def copy(self) -> Self:
        return deepcopy(self)

    def set_reader(
        self,
        value: TDatapoint,
        ts: dt.datetime | None = None,
    ) -> None:
        self.__value_read = value
        self.__ts_read = ts or dt.datetime.utcnow()

    def set_writer(
        self,
        value: TDatapoint,
        ts: dt.datetime | None = None,
    ) -> None:
        self.__value_write = value
        self.__ts_write = ts or dt.datetime.utcnow()


_datapoints_classes: dict[str, Type[DatapointBase[Any]]] = {}


def define_class_name(json: str) -> str:
    return DatapointClass.parse_raw(json).class_name


def define_class(class_name: str) -> Type[DatapointBase[Any]]:
    try:
        return _datapoints_classes[class_name]
    except KeyError:
        msg = "В словаре datapoints_dict нет записи для класса {0}".format(
            class_name,
        )
        logger.exception(msg)
        raise


def parse_datapoint_json(json: str) -> DatapointBase[Any]:
    class_name = define_class_name(json)
    class_ = define_class(class_name)
    return class_.from_json(json)


TDatapointsCollection: TypeAlias = dict[UUID, DatapointBase[Any]]
datapoints_collection: TDatapointsCollection = {}
