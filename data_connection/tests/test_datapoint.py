from uuid import UUID

from data_connection.datapoints import DatapointBool, datapoints_collection

from data_connection.datapoints.datapoint_base import (
    define_class_name,
    parse_datapoint_json,
)


def test_json():
    dp = DatapointBool("1ef282ca-a531-43cd-bb4d-1126fadf96a2")
    json = dp.to_json()
    assert define_class_name(json) == DatapointBool.__name__
    dp_from_json = parse_datapoint_json(json)
    assert dp == dp_from_json


def test_datapoints_collection():
    dp_uuid = UUID("56eaba9e-9a4a-4873-a618-aed658dd8525")
    dp = DatapointBool(dp_uuid)
    assert dp in datapoints_collection.values()
    assert dp_uuid in datapoints_collection.keys()


def test_uuid_duplicate():
    uuid = UUID("1dd049d1-9964-41fc-a920-e32dfe078675")
    DatapointBool(uuid)
    try:
        DatapointBool(uuid)
    except KeyError:
        return
    assert False


def test_copy():
    dp1 = DatapointBool("c1d02af7-ea93-48d0-ab7f-058ad504ea42")
    dp2 = dp1.copy()
    assert repr(dp1) == repr(dp2)
    assert id(dp1) != id(dp2)
