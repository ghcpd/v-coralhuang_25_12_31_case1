from explain import DELETE, Explanation, explain_config_value


def test_nested_only_base():
    e = explain_config_value(
        "db.timeout",
        base={"db": {"timeout": 30}},
        env={},
        override={},
    )
    assert e == Explanation(
        final_value=30,
        source="base",
        overridden=False,
        override_chain=["base"],
    )


def test_nested_base_overridden_by_env():
    e = explain_config_value(
        "db.timeout",
        base={"db": {"timeout": 30}},
        env={"db": {"timeout": 20}},
        override={},
    )
    assert e == Explanation(
        final_value=20,
        source="env",
        overridden=True,
        override_chain=["base", "env"],
    )


def test_nested_env_overridden_by_override():
    e = explain_config_value(
        "db.timeout",
        base={},
        env={"db": {"timeout": 20}},
        override={"db": {"timeout": 10}},
    )
    assert e == Explanation(
        final_value=10,
        source="override",
        overridden=True,
        override_chain=["env", "override"],
    )


def test_explicit_none_is_value_and_has_source():
    e = explain_config_value(
        "db.timeout",
        base={"db": {"timeout": 30}},
        env={"db": {"timeout": 20}},
        override={"db": {"timeout": None}},
    )
    assert e == Explanation(
        final_value=None,
        source="override",
        overridden=True,
        override_chain=["base", "env", "override"],
    )


def test_delete_semantics_suppresses_lower_values():
    e = explain_config_value(
        "db.timeout",
        base={"db": {"timeout": 30}},
        env={"db": {"timeout": 20}},
        override={"db": {"timeout": DELETE}},
    )
    assert e == Explanation(
        final_value=None,
        source="missing",
        overridden=True,
        override_chain=["base", "env", "override"],
    )


def test_delete_semantics_when_only_base_and_override_delete():
    e = explain_config_value(
        "db.timeout",
        base={"db": {"timeout": 30}},
        env={},
        override={"db": {"timeout": DELETE}},
    )
    assert e == Explanation(
        final_value=None,
        source="missing",
        overridden=True,
        override_chain=["base", "override"],
    )


def test_delete_in_env_without_override():
    e = explain_config_value(
        "db.timeout",
        base={"db": {"timeout": 30}},
        env={"db": {"timeout": DELETE}},
        override={},
    )
    assert e == Explanation(
        final_value=None,
        source="missing",
        overridden=True,
        override_chain=["base", "env"],
    )


def test_missing_nested_key_everywhere():
    e = explain_config_value(
        "db.retries",
        base={"db": {"timeout": 30}},
        env={"db": {"timeout": 20}},
        override={"db": {"timeout": 10}},
    )
    assert e == Explanation(
        final_value=None,
        source="missing",
        overridden=False,
        override_chain=[],
    )


def test_intermediate_not_a_dict_counts_as_missing():
    e = explain_config_value(
        "db.timeout",
        base={"db": 123},
        env={},
        override={},
    )
    assert e == Explanation(
        final_value=None,
        source="missing",
        overridden=False,
        override_chain=[],
    )
