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


def test_float_value_falls_back_to_zero_for_invalid_scalars() -> None:
    assert value_coercion.float_value(7) == 7.0
    assert value_coercion.float_value("9.5") == 9.5
    assert value_coercion.float_value("") == 0.0
    assert value_coercion.float_value("bad") == 0.0


def test_normalize_string_and_token_collapse_whitespace_and_delimiters() -> None:
    assert value_coercion.normalize_string("  Alpha   beta  ") == "Alpha beta"
    assert value_coercion.normalize_token(" Alpha-Beta  Gamma ") == "alpha_beta_gamma"


def test_normalize_string_list_dedupes_and_honors_limit() -> None:
    assert value_coercion.normalize_string_list([" Alpha ", "", "Beta", "Alpha", "Gamma"], limit=2) == [
        "Alpha",
        "Beta",
    ]
    assert value_coercion.normalize_string_list(" Solo ") == ["Solo"]
    assert value_coercion.normalize_string_list(None) == []


def test_dedupe_strings_trims_dedupes_and_honors_limit() -> None:
    assert value_coercion.dedupe_strings([" Alpha ", "", "Beta", "Alpha", "Gamma"], limit=2) == [
        "Alpha",
        "Beta",
    ]


def test_string_rows_requires_list_by_default_and_can_allow_scalars_or_sequences() -> None:
    assert value_coercion.string_rows([" Alpha ", "", "Beta", "Alpha"]) == ["Alpha", "Beta"]
    assert value_coercion.string_rows((" Alpha ", "Beta")) == []
    assert value_coercion.string_rows((" Alpha ", "Beta"), allow_sequence=True) == ["Alpha", "Beta"]
    assert value_coercion.string_rows("Solo") == []
    assert value_coercion.string_rows("Solo", allow_scalar=True) == ["Solo"]
    assert value_coercion.string_rows(None) == []


def test_bool_value_parses_common_string_forms_and_defaults() -> None:
    assert value_coercion.bool_value(True) is True
    assert value_coercion.bool_value(" yes ") is True
    assert value_coercion.bool_value("OFF") is False
    assert value_coercion.bool_value("unknown", default=True) is True
