"""Workflow Conditional Condition 纯计算求值模块。

职责：在冻结的有限 JSON DSL 上执行严格、确定性的条件判断，并提供结构校验。
边界：只读取调用方传入的 Runtime state_data，不访问数据库、网络、文件、Provider 或执行任意代码。
关键依赖：Python 标准库；输入必须为 JSON-compatible 基础类型。
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

MAX_DEPTH = 8
MAX_NODES = 64
_MISSING = object()
_COMPARISON_OPS = {"eq", "ne", "gt", "gte", "lt", "lte", "in", "contains"}
_LOGICAL_OPS = {"and", "or", "not"}
_ALLOWED_OPS = _COMPARISON_OPS | _LOGICAL_OPS


@dataclass(frozen=True)
class WorkflowConditionEvaluation:
    """条件求值结果及其确定性命中状态。"""

    matched: bool


class WorkflowConditionEvaluator:
    """校验并求值有限 Condition DSL。"""

    @classmethod
    def validate(cls, condition: object) -> None:
        """校验条件结构、深度与节点数量，不执行条件。

        Args:
            condition: 待校验的有限 JSON 条件对象。

        Returns:
            无返回值；校验通过表示该条件可以安全求值。

        Raises:
            ValueError: 条件结构、操作符、路径、操作数或复杂度超出 Contract。
        """
        count = [0]
        cls._validate(condition, depth=1, count=count)

    @classmethod
    def evaluate(cls, condition: Mapping[str, Any], state_data: Mapping[str, Any]) -> WorkflowConditionEvaluation:
        """在当前 Runtime state_data 上确定性求值条件。

        Args:
            condition: 已符合 Condition DSL 的条件对象。
            state_data: 当前 Runtime 状态，只允许通过固定点号路径读取。

        Returns:
            包含 `matched` 布尔值的不可变求值结果。

        Raises:
            ValueError: 输入不符合 Contract 或比较操作数类型不合法。
        """
        cls.validate(condition)
        if not isinstance(state_data, Mapping):
            raise ValueError("Condition state_data 必须为对象")
        return WorkflowConditionEvaluation(matched=cls._evaluate(condition, state_data))

    @classmethod
    def _validate(cls, condition: object, *, depth: int, count: list[int]) -> None:
        if depth > MAX_DEPTH:
            raise ValueError(f"Condition 最大深度不能超过 {MAX_DEPTH}")
        if not isinstance(condition, dict):
            raise ValueError("Condition 必须为对象")
        count[0] += 1
        if count[0] > MAX_NODES:
            raise ValueError(f"Condition 节点数不能超过 {MAX_NODES}")
        if set(condition) - {"op", "path", "value", "conditions", "condition"}:
            raise ValueError("Condition 包含未允许字段")
        op = condition.get("op")
        if op not in _ALLOWED_OPS:
            raise ValueError(f"Condition op 不支持: {op}")
        if op in _COMPARISON_OPS:
            if not isinstance(condition.get("path"), str) or not condition["path"]:
                raise ValueError("Condition comparison 必须包含非空 path")
            if any(part == "" for part in condition["path"].split(".")):
                raise ValueError("Condition path 不能包含空路径段")
            if "value" not in condition:
                raise ValueError(f"Condition {op} 必须包含 value")
            if op == "in" and not isinstance(condition["value"], list):
                raise ValueError("Condition in 的 value 必须为数组")
            if op == "contains" and not isinstance(condition["value"], (str, int, float, bool, list, dict)) and condition["value"] is not None:
                raise ValueError("Condition contains 的 value 必须为 JSON 值")
            if op in {"gt", "gte", "lt", "lte"} and not cls._is_number(condition.get("value")):
                raise ValueError(f"Condition {op} 的 value 必须为 number")
            return
        if op in {"and", "or"}:
            conditions = condition.get("conditions")
            if not isinstance(conditions, list) or not conditions:
                raise ValueError(f"Condition {op} 必须包含非空 conditions 数组")
            for child in conditions:
                cls._validate(child, depth=depth + 1, count=count)
            return
        if set(condition) != {"op", "condition"}:
            raise ValueError("Condition not 必须只包含 op / condition")
        cls._validate(condition["condition"], depth=depth + 1, count=count)

    @classmethod
    def _evaluate(cls, condition: Mapping[str, Any], state_data: Mapping[str, Any]) -> bool:
        op = condition["op"]
        if op == "and":
            return all(cls._evaluate(item, state_data) for item in condition["conditions"])
        if op == "or":
            return any(cls._evaluate(item, state_data) for item in condition["conditions"])
        if op == "not":
            return not cls._evaluate(condition["condition"], state_data)

        actual = cls._read_path(state_data, condition["path"])
        if actual is _MISSING:
            return False
        expected = condition.get("value")
        if op == "eq":
            return cls._strict_equal(actual, expected)
        if op == "ne":
            return not cls._strict_equal(actual, expected)
        if op in {"gt", "gte", "lt", "lte"}:
            if not cls._is_number(actual) or not cls._is_number(expected):
                raise ValueError(f"Condition {op} 双方必须为 number")
            return {"gt": actual > expected, "gte": actual >= expected, "lt": actual < expected, "lte": actual <= expected}[op]
        if op == "in":
            return any(cls._strict_equal(actual, item) for item in expected)
        if isinstance(actual, str):
            if not isinstance(expected, str):
                raise ValueError("Condition contains 字符串操作数必须均为字符串")
            return expected in actual
        if isinstance(actual, list):
            return any(cls._strict_equal(actual_item, expected) for actual_item in actual)
        raise ValueError("Condition contains 仅允许字符串包含字符串，或数组包含严格相等元素")

    @staticmethod
    def _read_path(state_data: Mapping[str, Any], path: str) -> object:
        current: Any = state_data
        for part in path.split("."):
            if not isinstance(current, Mapping) or part not in current:
                return _MISSING
            current = current[part]
        return current

    @staticmethod
    def _is_number(value: object) -> bool:
        return isinstance(value, (int, float)) and not isinstance(value, bool)

    @classmethod
    def _strict_equal(cls, left: object, right: object) -> bool:
        if isinstance(left, bool) or isinstance(right, bool):
            return type(left) is type(right) and left == right
        if cls._is_number(left) and cls._is_number(right):
            return left == right
        if type(left) is not type(right):
            return False
        if isinstance(left, list) and isinstance(right, list):
            return len(left) == len(right) and all(cls._strict_equal(a, b) for a, b in zip(left, right))
        if isinstance(left, dict) and isinstance(right, dict):
            return left.keys() == right.keys() and all(cls._strict_equal(left[key], right[key]) for key in left)
        return left == right
