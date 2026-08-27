"""Workflow Condition Evaluator 单元测试。

职责：验证有限 JSON Condition DSL 的结构约束、严格类型比较、短路求值与安全边界。
边界：只验证纯内存 Condition Evaluator，不连接数据库、Worker、Runtime 或 Provider。
关键依赖：WorkflowConditionEvaluator。
"""

import pytest

from app.services.workflow.checkpoint.recovery.condition import WorkflowConditionEvaluator


def evaluate(condition: dict, state: dict | None = None) -> bool:
    """执行条件并返回命中结果。

    Args:
        condition: 待求值的 Condition DSL。
        state: Runtime state_data；未提供时使用空对象。

    Returns:
        条件是否命中。
    """
    return WorkflowConditionEvaluator.evaluate(condition, state or {}).matched


@pytest.mark.parametrize(
    ("op", "actual", "expected", "matched"),
    [
        ("eq", "approved", "approved", True),
        ("eq", "approved", "rejected", False),
        ("ne", "approved", "rejected", True),
        ("ne", "approved", "approved", False),
        ("gt", 10, 9, True),
        ("gte", 10, 10, True),
        ("gte", 10, 11, False),
        ("lt", 10, 11, True),
        ("lte", 10, 10, True),
        ("lte", 10, 9, False),
    ],
)
def test_comparison_operators_are_deterministic(op: str, actual: object, expected: object, matched: bool) -> None:
    condition = {"op": op, "path": "result.value", "value": expected}
    assert evaluate(condition, {"result": {"value": actual}}) is matched


def test_strict_json_types_do_not_treat_bool_as_number() -> None:
    assert evaluate({"op": "eq", "path": "value", "value": 1}, {"value": True}) is False
    assert evaluate({"op": "eq", "path": "value", "value": True}, {"value": 1}) is False
    assert evaluate({"op": "ne", "path": "value", "value": 1}, {"value": True}) is True


def test_numeric_comparison_rejects_bool() -> None:
    with pytest.raises(ValueError, match="value 必须为 number"):
        WorkflowConditionEvaluator.validate({"op": "gt", "path": "value", "value": True})

    with pytest.raises(ValueError, match="双方必须为 number"):
        evaluate({"op": "gt", "path": "value", "value": 1}, {"value": False})


def test_in_uses_strict_element_matching() -> None:
    condition = {"op": "in", "path": "value", "value": [1, "1", True]}
    assert evaluate(condition, {"value": 1}) is True
    assert evaluate(condition, {"value": "1"}) is True
    assert evaluate(condition, {"value": False}) is False


def test_contains_supports_string_and_array_semantics() -> None:
    assert evaluate({"op": "contains", "path": "message", "value": "approved"}, {"message": "request approved"}) is True
    assert evaluate({"op": "contains", "path": "items", "value": "a"}, {"items": ["a", "b"]}) is True
    assert evaluate({"op": "contains", "path": "items", "value": 1}, {"items": [1, 2]}) is True
    assert evaluate({"op": "contains", "path": "items", "value": True}, {"items": [1, True]}) is True


def test_contains_rejects_incompatible_runtime_type() -> None:
    with pytest.raises(ValueError, match="字符串操作数必须均为字符串"):
        evaluate({"op": "contains", "path": "message", "value": 1}, {"message": "123"})

    with pytest.raises(ValueError, match="仅允许字符串包含字符串"):
        evaluate({"op": "contains", "path": "value", "value": "a"}, {"value": {"a": 1}})


def test_missing_path_is_not_implicitly_converted_to_null() -> None:
    condition = {"op": "eq", "path": "result.status", "value": None}
    assert evaluate(condition, {"result": {}}) is False
    assert evaluate({"op": "ne", "path": "result.status", "value": None}, {"result": {}}) is False
    assert evaluate(condition, {"result": {"status": None}}) is True


def test_logical_operators_support_short_circuit_evaluation() -> None:
    invalid_runtime_contains = {"op": "contains", "path": "value", "value": 1}
    assert evaluate(
        {"op": "and", "conditions": [
            {"op": "eq", "path": "enabled", "value": False},
            invalid_runtime_contains,
        ]},
        {"enabled": False, "value": "text"},
    ) is False

    assert evaluate(
        {"op": "or", "conditions": [
            {"op": "eq", "path": "enabled", "value": True},
            invalid_runtime_contains,
        ]},
        {"enabled": True, "value": "text"},
    ) is True

    assert evaluate(
        {"op": "not", "condition": {"op": "eq", "path": "enabled", "value": True}},
        {"enabled": False},
    ) is True


def test_recursive_strict_equality_covers_json_arrays_and_objects() -> None:
    value = {"items": [1, {"name": "a"}], "enabled": True}
    assert evaluate({"op": "eq", "path": "value", "value": value}, {"value": value}) is True
    assert evaluate(
        {"op": "eq", "path": "value", "value": {"items": [1, {"name": "b"}], "enabled": True}},
        {"value": value},
    ) is False


@pytest.mark.parametrize(
    "condition",
    [
        {"op": "eq", "path": "value"},
        {"op": "in", "path": "value", "value": "not-array"},
        {"op": "and", "conditions": []},
        {"op": "or", "conditions": []},
        {"op": "not", "condition": {"op": "eq", "path": "value", "value": 1}, "value": 1},
        {"op": "eq", "path": "value", "value": 1, "unexpected": True},
        {"op": "eq", "path": "value..status", "value": 1},
    ],
)
def test_invalid_condition_structure_is_rejected(condition: dict) -> None:
    with pytest.raises(ValueError):
        WorkflowConditionEvaluator.validate(condition)


def test_non_mapping_state_is_rejected() -> None:
    with pytest.raises(ValueError, match="state_data 必须为对象"):
        WorkflowConditionEvaluator.evaluate(
            {"op": "eq", "path": "value", "value": 1},
            [],
        )


def test_condition_depth_limit_is_enforced() -> None:
    condition = {"op": "eq", "path": "value", "value": True}
    for _ in range(8):
        condition = {"op": "not", "condition": condition}

    with pytest.raises(ValueError, match="最大深度"):
        WorkflowConditionEvaluator.validate(condition)


def test_condition_node_limit_is_enforced() -> None:
    condition = {
        "op": "and",
        "conditions": [
            {"op": "eq", "path": f"value{i}", "value": i}
            for i in range(64)
        ],
    }

    with pytest.raises(ValueError, match="节点数"):
        WorkflowConditionEvaluator.validate(condition)


def test_all_comparison_operators_require_value_field() -> None:
    for op in ("eq", "ne", "gt", "gte", "lt", "lte", "in", "contains"):
        with pytest.raises(ValueError, match="必须包含 value"):
            WorkflowConditionEvaluator.validate({"op": op, "path": "value"})
