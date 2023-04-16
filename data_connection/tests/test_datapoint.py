from uuid import UUID

from data_connection.datapoints import (
    DatapointBool,
    DatapointInt,
    DatapointFloat,
    DatapointStr,
    datapoints_collection,
)

from data_connection.datapoints.datapoint_base import (
    _define_class_name,  # type: ignore
    parse_datapoint_json,
)


def test_json():
    dp_bool = DatapointBool("1ef282ca-a531-43cd-bb4d-1126fadf96a2")
    json = dp_bool.to_json()
    assert _define_class_name(json) == DatapointBool.__name__
    assert dp_bool == parse_datapoint_json(json)

    dp_int = DatapointInt("80ee5650-11ab-479a-837b-da07207f0d5c")
    json = dp_int.to_json()
    assert _define_class_name(json) == DatapointInt.__name__
    assert dp_int == parse_datapoint_json(json)

    dp_float = DatapointFloat("1399c9cd-f8d6-4b97-a3b8-2a3c3a014408")
    json = dp_float.to_json()
    assert _define_class_name(json) == DatapointFloat.__name__
    assert dp_float == parse_datapoint_json(json)

    dp_str = DatapointStr("1935ab5b-a16d-4e3b-8deb-d4c5057fa75b")
    json = dp_str.to_json()
    assert _define_class_name(json) == DatapointStr.__name__
    assert dp_str == parse_datapoint_json(json)


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
