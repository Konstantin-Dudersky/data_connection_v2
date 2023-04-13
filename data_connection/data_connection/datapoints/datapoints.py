from .datapoint_base import DatapointBase


class DatapointBool(DatapointBase[bool]):
    @classmethod
    def _set_default_value(cls, value: bool | None) -> bool:
        if value is None:
            return bool(0)
        return bool(value)


class DatapointFloat(DatapointBase[float]):
    @classmethod
    def _set_default_value(cls, value: float | None) -> float:
        if value is None:
            return float(0)
        return float(value)


class DatapointInt(DatapointBase[int]):
    @classmethod
    def _set_default_value(cls, value: int | None) -> int:
        if value is None:
            return int(0)
        return int(value)


class DatapointStr(DatapointBase[str]):
    @classmethod
    def _set_default_value(cls, value: str | None) -> str:
        if value is None:
            return str("")
        return str(value)
