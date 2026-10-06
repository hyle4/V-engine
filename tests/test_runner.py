from pathlib import Path

import pytest

from vengine.grading import grade
from vengine.models import CodeCase, CodeSpec, ContentBlock, ExerciseRevision
from vengine.runner import available, available_runners


def test_runner_availability_reporting():
    runners = available_runners()
    assert "podman" in runners
    assert "docker" in runners
    assert "local" in runners


def test_local_runner_execution_when_enabled(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    monkeypatch.setenv("VENGINE_ALLOW_LOCAL_RUNNER", "1")
    monkeypatch.setenv("VENGINE_DEV_MODE", "1")
    ok, reason = available()
    assert ok is True
    assert "local" in reason

    item = ExerciseRevision(
        prompt=[ContentBlock(text="Two Sum")],
        interaction=CodeSpec(
            language="python",
            entrypoint="twoSum",
            entrypoint_type="method",
            class_name="Solution",
            cases=[
                CodeCase(input=[[2, 7, 11, 15], 9], expected=[0, 1], visible=True)
            ],
        ),
    )
    solution = (
        "class Solution:\n"
        "    def twoSum(self, nums, target):\n"
        "        d = {}\n"
        "        for i, x in enumerate(nums):\n"
        "            if target - x in d:\n"
        "                return [d[target - x], i]\n"
        "            d[x] = i\n"
        "        return []\n"
    )
    result = grade(item, solution)
    assert result.outcome == "correct"
    assert result.score == 1.0
    assert len(result.details.get("visible_cases", [])) == 1
    assert result.details["visible_cases"][0]["actual"] == [0, 1]
    assert result.details["visible_cases"][0]["passed"] is True


def test_api_run_sample_endpoint(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    from fastapi.testclient import TestClient

    from vengine.api import create_app
    from vengine.store import Store

    monkeypatch.setenv("VENGINE_ALLOW_LOCAL_RUNNER", "1")
    monkeypatch.setenv("VENGINE_DEV_MODE", "1")
    store = Store(tmp_path)
    item = ExerciseRevision(
        title="Two Sum",
        prompt=[ContentBlock(text="Two Sum problem")],
        interaction=CodeSpec(
            language="python",
            entrypoint="twoSum",
            entrypoint_type="method",
            class_name="Solution",
            cases=[
                CodeCase(input=[[2, 7, 11, 15], 9], expected=[0, 1], visible=True, name="Case 1"),
                CodeCase(input=[[3, 2, 4], 6], expected=[1, 2], visible=False, name="Case 2"),
            ],
        ),
        status="approved",
        approved_at=ExerciseRevision(prompt=[ContentBlock(text="x")], interaction=CodeSpec()).created_at,
    )
    store.save_revision(item)

    client = TestClient(create_app(tmp_path))
    solution = "class Solution:\n    def twoSum(self, nums, target):\n        return [0, 1]\n"

    # Test /run endpoint
    res = client.post(f"/api/exercises/{item.exercise_id}/run", json={"response": solution})
    assert res.status_code == 200, res.text
    data = res.json()["result"]
    assert data["outcome"] == "correct"
    # Hidden case was not evaluated in sample run!
    assert len(data["details"]["visible_cases"]) == 1

    # Verify NO attempt was stored
    assert len(store.attempts(item.exercise_id)) == 0

    # Now test /submit endpoint
    res_submit = client.post(f"/api/exercises/{item.exercise_id}/submit", json={"response": solution})
    assert res_submit.status_code == 200
    # Case 2 failed because [0, 1] != [1, 2]
    assert res_submit.json()["attempt"]["grade"]["outcome"] == "partial"
    # Attempt was stored!
    assert len(store.attempts(item.exercise_id)) == 1
