from copy import deepcopy
from ipaddress import IPv4Address
from uuid import uuid4
from typing import NamedTuple, cast

import pytest
from data_connection.datapoints import DatapointInt, datapoints_collection
from data_connection.redis_sync.redis_sync import RedisSync


class TestInstance(NamedTuple):
    dp1: DatapointInt
    dp2: DatapointInt
    redis1: RedisSync
    redis2: RedisSync


@pytest.fixture
def data() -> TestInstance:
    uuid = uuid4()
    dp1 = DatapointInt(uuid=uuid)
    dpc1 = datapoints_collection
    dpc2 = deepcopy(datapoints_collection)
    dp2 = cast(DatapointInt, dpc2[uuid])
    assert id(dpc1) != id(dpc2)
    assert id(dp1) != id(dp2)
    return TestInstance(
        dp1=dp1,
        dp2=dp2,
        redis1=RedisSync(
            datapoints_call=dpc1,
            host=IPv4Address("192.168.101.12"),
        ),
        redis2=RedisSync(
            datapoints_call=dpc2,
            host=IPv4Address("192.168.101.12"),
        ),
    )
