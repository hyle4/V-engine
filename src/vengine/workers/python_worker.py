"""Executed inside the isolated container or sandbox runner."""
from __future__ import annotations

import collections
import contextlib
import heapq
import inspect
import io
import itertools
import json
import math
import sqlite3
import sys
import time
from typing import Any


class ListNode:
    def __init__(self, val: Any = 0, next: ListNode | None = None):
        self.val = val
        self.next = next

    @classmethod
    def from_list(cls, items: list[Any] | None) -> ListNode | None:
        if not items:
            return None
        head = cls(items[0])
        curr = head
        for item in items[1:]:
            curr.next = cls(item)
            curr = curr.next
        return head

    def to_list(self) -> list[Any]:
        result = []
        curr: ListNode | None = self
        visited = set()
        while curr is not None:
            if id(curr) in visited:
                result.append("[cycle]")
                break
            visited.add(id(curr))
            result.append(curr.val)
            curr = curr.next
        return result

    def __eq__(self, other: object) -> bool:
        if isinstance(other, list):
            return self.to_list() == other
        if isinstance(other, ListNode):
            return self.to_list() == other.to_list()
        return False

    def __repr__(self) -> str:
        return f"ListNode({self.to_list()})"


class TreeNode:
    def __init__(self, val: Any = 0, left: TreeNode | None = None, right: TreeNode | None = None):
        self.val = val
        self.left = left
        self.right = right

    @classmethod
    def from_list(cls, items: list[Any] | None) -> TreeNode | None:
        if not items:
            return None
        nodes = [cls(val) if val is not None else None for val in items]
        kids = nodes[::-1]
        root = kids.pop()
        for node in nodes:
            if node:
                if kids:
                    node.left = kids.pop()
                if kids:
                    node.right = kids.pop()
        return root

    def to_list(self) -> list[Any]:
        result: list[Any] = []
        queue: list[TreeNode | None] = [self]
        while queue:
            node = queue.pop(0)
            if node is not None:
                result.append(node.val)
                queue.append(node.left)
                queue.append(node.right)
            else:
                result.append(None)
        while result and result[-1] is None:
            result.pop()
        return result

    def __eq__(self, other: object) -> bool:
        if isinstance(other, list):
            return self.to_list() == other
        if isinstance(other, TreeNode):
            return self.to_list() == other.to_list()
        return False

    def __repr__(self) -> str:
        return f"TreeNode({self.to_list()})"


def _serialize(obj: Any) -> Any:
    if isinstance(obj, (ListNode, TreeNode)):
        return obj.to_list()
    if isinstance(obj, (list, tuple)):
        return [_serialize(x) for x in obj]
    if isinstance(obj, dict):
        return {k: _serialize(v) for k, v in obj.items()}
    return obj


def _normalize_expected(got: Any, expected: Any) -> bool:
    if isinstance(got, (ListNode, TreeNode)):
        got = got.to_list()
    if isinstance(expected, (ListNode, TreeNode)):
        expected = expected.to_list()
    return got == expected


def result(passed: int, total: int, details: dict | None = None) -> dict:
    score = passed / total if total else None
    return {
        "outcome": "correct" if score == 1 else "partial" if score else "incorrect" if score is not None else "ungraded",
        "score": score,
        "feedback": "",
        "details": details or {},
    }


def main():
    payload = json.load(sys.stdin)
    spec, answer = payload["spec"], payload["response"]
    try:
        if spec["kind"] == "code":
            cases = spec.get("cases", [])
            passed = 0
            details = []
            if spec.get("protocol", "function") == "function":
                env = {
                    "ListNode": ListNode,
                    "TreeNode": TreeNode,
                    "collections": collections,
                    "heapq": heapq,
                    "itertools": itertools,
                    "math": math,
                }
                exec_stdout = io.StringIO()
                with contextlib.redirect_stdout(exec_stdout):
                    exec(answer, env)

                entrypoint = spec.get("entrypoint", "solve")
                class_name = spec.get("class_name", "Solution")

                # Resolve callable
                fn = None
                if entrypoint in env:
                    target = env[entrypoint]
                    if inspect.isclass(target):
                        inst = target()
                        fn = getattr(inst, "solve", None) or inst
                    else:
                        fn = target
                elif class_name in env:
                    cls_obj = env[class_name]
                    inst = cls_obj() if inspect.isclass(cls_obj) else cls_obj
                    if hasattr(inst, entrypoint):
                        fn = getattr(inst, entrypoint)
                elif "Solution" in env:
                    cls_obj = env["Solution"]
                    inst = cls_obj() if inspect.isclass(cls_obj) else cls_obj
                    if hasattr(inst, entrypoint):
                        fn = getattr(inst, entrypoint)

                if fn is None or not callable(fn):
                    output = {"outcome": "error", "score": None,
                              "feedback": f"Could not find callable entrypoint '{entrypoint}'",
                              "details": {}}
                    print(json.dumps(output))
                    return

                try:
                    sig = inspect.signature(fn)
                    param_count = len(sig.parameters)
                except (ValueError, TypeError):
                    param_count = -1

                structure_type = spec.get("structure_type", "standard")

                for case in cases:
                    case_input = case["input"]
                    # Convert inputs for data structures if required
                    if structure_type == "linked_list" and isinstance(case_input, list):
                        if param_count == 1:
                            prepared_args = [ListNode.from_list(case_input)]
                        else:
                            prepared_args = [ListNode.from_list(x) if isinstance(x, list) else x for x in case_input]
                    elif structure_type == "tree" and isinstance(case_input, list):
                        if param_count == 1:
                            prepared_args = [TreeNode.from_list(case_input)]
                        else:
                            prepared_args = [TreeNode.from_list(x) if isinstance(x, list) else x for x in case_input]
                    elif isinstance(case_input, list):
                        if param_count == 1:
                            if len(case_input) == 1 and isinstance(case_input[0], list):
                                prepared_args = [case_input[0]]
                            else:
                                prepared_args = [case_input]
                        else:
                            prepared_args = case_input
                    elif isinstance(case_input, dict):
                        prepared_args = []
                    else:
                        prepared_args = [case_input]

                    case_stdout = io.StringIO()
                    start_time = time.perf_counter()
                    case_error = None
                    got = None
                    try:
                        with contextlib.redirect_stdout(case_stdout):
                            if isinstance(case_input, dict) and param_count != 1:
                                got = fn(**case_input)
                            else:
                                got = fn(*prepared_args)
                    except Exception as err:
                        case_error = f"{type(err).__name__}: {err}"

                    duration_ms = round((time.perf_counter() - start_time) * 1000, 2)
                    ok = case_error is None and _normalize_expected(got, case["expected"])
                    if ok:
                        passed += 1

                    if case.get("visible", False):
                        details.append({
                            "name": case.get("name"),
                            "input": case["input"],
                            "expected": _serialize(case["expected"]),
                            "actual": _serialize(got) if case_error is None else None,
                            "stdout": case_stdout.getvalue(),
                            "error": case_error,
                            "duration_ms": duration_ms,
                            "passed": ok,
                        })
            else:
                for case in cases:
                    stream_in, stream_out = io.StringIO(str(case["input"])), io.StringIO()
                    old_in, old_out = sys.stdin, sys.stdout
                    case_error = None
                    try:
                        sys.stdin, sys.stdout = stream_in, stream_out
                        exec(answer, {"__name__": "__main__"})
                        ok = stream_out.getvalue().strip() == str(case["expected"]).strip()
                    except Exception as err:
                        ok = False
                        case_error = str(err)
                    finally:
                        sys.stdin, sys.stdout = old_in, old_out
                    if ok:
                        passed += 1
                    if case.get("visible", False):
                        details.append({
                            "name": case.get("name"),
                            "input": case["input"],
                            "expected": case["expected"],
                            "actual": stream_out.getvalue().strip() if not case_error else None,
                            "error": case_error,
                            "passed": ok,
                        })
            output = result(passed, len(cases), {"visible_cases": details})
        else:
            def query(connection, sql):
                if not sql.lstrip().lower().startswith(("select", "with")):
                    raise ValueError("Only SELECT queries are allowed")
                return connection.execute(sql).fetchall()

            con = sqlite3.connect(":memory:")
            con.executescript(spec["setup_sql"])
            expected = query(con, spec["reference_query"])
            got = query(con, answer)
            if not spec.get("order_sensitive", False):
                expected = sorted(map(repr, expected))
                got = sorted(map(repr, got))
            output = result(int(got == expected), 1)
    except Exception as exc:
        output = {"outcome": "error", "score": None, "feedback": str(exc)[:300], "details": {}}
    print(json.dumps(output))


if __name__ == "__main__":
    main()

