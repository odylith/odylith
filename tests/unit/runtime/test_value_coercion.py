from odylith.runtime.common import value_coercion


def test_mapping_copy_returns_plain_dict_for_mappings_only() -> None:
    assert value_coercion.mapping_copy({"a": 1}) == {"a": 1}
    assert value_coercion.mapping_copy(None) == {}
    assert value_coercion.mapping_copy(["a"]) == {}


def test_int_value_falls_back_to_zero_for_invalid_scalars() -> None:
    assert value_coercion.int_value(7) == 7
    assert value_coercion.int_value("9") == 9
    assert value_coercion.int_value("") == 0
    assert value_coercion.int_value("bad") == 0
