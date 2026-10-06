"""Trusted fixtures exercise worker logic; production submissions still need gVisor."""

import json
import subprocess
import sys
from pathlib import Path

from vengine.runner import WORKERS


def invoke(worker: Path, payload: dict, executable: str) -> dict:
    result = subprocess.run([executable, str(worker)], input=json.dumps(payload),
                            capture_output=True, text=True, timeout=5, check=True)
    return json.loads(result.stdout)


def test_python_function_and_sql_worker():
    code = {"spec": {"kind": "code", "protocol": "function", "entrypoint": "solve",
                     "cases": [{"input": [2, 3], "expected": 5, "visible": True},
                               {"input": [4, 5], "expected": 9, "visible": False}]},
            "response": "def solve(a, b): return a + b"}
    result = invoke(WORKERS / "python_worker.py", code, sys.executable)
    assert result["outcome"] == "correct"
    assert len(result["details"]["visible_cases"]) == 1
    sql = {"spec": {"kind": "sql", "setup_sql": "CREATE TABLE n(x); INSERT INTO n VALUES (1),(2);",
                    "reference_query": "SELECT x FROM n WHERE x > 1", "order_sensitive": False},
           "response": "SELECT x FROM n WHERE x = 2"}
    assert invoke(WORKERS / "python_worker.py", sql, sys.executable)["outcome"] == "correct"


def test_javascript_function_worker():
    payload = {"spec": {"kind": "code", "protocol": "function", "entrypoint": "solve",
                        "cases": [{"input": [1, 2], "expected": 3, "visible": True}]},
               "response": "function solve(a, b) { return a + b; }"}
    assert invoke(WORKERS / "node_worker.js", payload, "node")["outcome"] == "correct"
    payload["spec"]["protocol"] = "stdio"
    payload["spec"]["cases"] = [{"input": "2 3\n", "expected": "5", "visible": True}]
    payload["response"] = "const [a,b] = require('fs').readFileSync(0,'utf8').trim().split(' ').map(Number); console.log(a+b)"
    assert invoke(WORKERS / "node_worker.js", payload, "node")["outcome"] == "correct"


def test_python_solution_class_and_data_structures():
    # 1. Solution class with method entrypoint
    payload = {
        "spec": {
            "kind": "code",
            "protocol": "function",
            "entrypoint": "twoSum",
            "entrypoint_type": "method",
            "class_name": "Solution",
            "cases": [
                {"input": [[2, 7, 11, 15], 9], "expected": [0, 1], "visible": True}
            ],
        },
        "response": (
            "class Solution:\n"
            "    def twoSum(self, nums, target):\n"
            "        seen = {}\n"
            "        for i, n in enumerate(nums):\n"
            "            if target - n in seen:\n"
            "                return [seen[target - n], i]\n"
            "            seen[n] = i\n"
            "        return []\n"
        ),
    }
    result = invoke(WORKERS / "python_worker.py", payload, sys.executable)
    assert result["outcome"] == "correct"
    assert result["details"]["visible_cases"][0]["actual"] == [0, 1]

    # 2. Single-list parameter function (not unpacked incorrectly)
    payload_single_list = {
        "spec": {
            "kind": "code",
            "protocol": "function",
            "entrypoint": "maxSubArray",
            "cases": [{"input": [-2, 1, -3, 4, -1, 2, 1, -5, 4], "expected": 6, "visible": True}],
        },
        "response": (
            "def maxSubArray(nums):\n"
            "    max_so_far = curr = nums[0]\n"
            "    for x in nums[1:]:\n"
            "        curr = max(x, curr + x)\n"
            "        max_so_far = max(max_so_far, curr)\n"
            "    return max_so_far\n"
        ),
    }
    result_sl = invoke(WORKERS / "python_worker.py", payload_single_list, sys.executable)
    assert result_sl["outcome"] == "correct"

    # 3. ListNode support
    payload_ll = {
        "spec": {
            "kind": "code",
            "protocol": "function",
            "entrypoint": "reverseList",
            "structure_type": "linked_list",
            "cases": [{"input": [1, 2, 3], "expected": [3, 2, 1], "visible": True}],
        },
        "response": (
            "def reverseList(head):\n"
            "    prev = None\n"
            "    curr = head\n"
            "    while curr:\n"
            "        nxt = curr.next\n"
            "        curr.next = prev\n"
            "        prev = curr\n"
            "        curr = nxt\n"
            "    return prev\n"
        ),
    }
    result_ll = invoke(WORKERS / "python_worker.py", payload_ll, sys.executable)
    assert result_ll["outcome"] == "correct"
    assert result_ll["details"]["visible_cases"][0]["actual"] == [3, 2, 1]

    # 4. TreeNode support
    payload_tree = {
        "spec": {
            "kind": "code",
            "protocol": "function",
            "entrypoint": "invertTree",
            "structure_type": "tree",
            "cases": [{"input": [4, 2, 7, 1, 3, 6, 9], "expected": [4, 7, 2, 9, 6, 3, 1], "visible": True}],
        },
        "response": (
            "def invertTree(root):\n"
            "    if not root: return None\n"
            "    root.left, root.right = invertTree(root.right), invertTree(root.left)\n"
            "    return root\n"
        ),
    }
    result_tree = invoke(WORKERS / "python_worker.py", payload_tree, sys.executable)
    assert result_tree["outcome"] == "correct"
    assert result_tree["details"]["visible_cases"][0]["actual"] == [4, 7, 2, 9, 6, 3, 1]
