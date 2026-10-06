"""The core generator creates a neutral package-backed project."""

import subprocess
import sys
from pathlib import Path

from fastapi.testclient import TestClient

from vengine.api import create_app
from vengine.project import load_project


def test_starter_is_independent_of_engine_source(tmp_path: Path):
    subprocess.run([sys.executable, "-m", "vengine.cli", "new", "course-lab",
                    "--target", str(tmp_path)], check=True, capture_output=True)
    project = tmp_path / "course-lab"
    assert not (project / "vengine").exists()
    assert (project / "app.py").exists()
    assert (project / "project_plugins.py").exists()
    assert "vengine[ai]>=0.3,<1" in (project / "pyproject.toml").read_text()
    assert (project / "AGENTS.md").exists()
    assert load_project(project).name == "course-lab"
    client = TestClient(create_app(project / "data", project_root=project))
    assert client.get("/api/project").json()["editable"] is True
    assert client.get("/api/health").json()["stats"]["approved"] == 0
