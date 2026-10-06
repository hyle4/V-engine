"""Execution sandboxes for code and SQL submissions."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

from .models import CodeSpec, GradeResult, SQLSpec

WORKERS = Path(__file__).parent / "workers"
PYTHON_IMAGE = os.environ.get("VENGINE_PYTHON_IMAGE", "docker.io/library/python:3.12-alpine")
NODE_IMAGE = os.environ.get("VENGINE_NODE_IMAGE", "docker.io/library/node:22-alpine")


def _images_ready(command: str) -> bool:
    for image in (PYTHON_IMAGE, NODE_IMAGE):
        try:
            result = subprocess.run([command, "image", "inspect", image], capture_output=True,
                                    timeout=5, check=False)
            if result.returncode:
                return False
        except (OSError, subprocess.TimeoutExpired):
            return False
    return True


def _check_podman() -> tuple[bool, str]:
    if not shutil.which("podman"):
        return False, "Podman is not installed. Install rootless Podman and gVisor/runsc to grade code."
    if not shutil.which("runsc"):
        return False, "gVisor/runsc is not installed. Code grading is disabled."
    try:
        result = subprocess.run(["podman", "info", "--format", "{{.Host.Security.Rootless}}"],
                                capture_output=True, text=True, timeout=10, check=False)
        if result.returncode or result.stdout.strip() != "true":
            return False, "Podman must run rootless. Code grading is disabled."
        if not _images_ready("podman"):
            return False, "Pull the configured Python and Node runner images first."
        return True, "ready"
    except Exception as exc:
        return False, f"Podman check failed: {exc}"


def _check_docker() -> tuple[bool, str]:
    if not shutil.which("docker"):
        return False, "Docker is not installed."
    try:
        result = subprocess.run(["docker", "info"],
                                capture_output=True, text=True, timeout=5, check=False)
        if result.returncode != 0:
            return False, "Docker daemon is not accessible."
        if not _images_ready("docker"):
            return False, "Pull the configured Python and Node runner images first."
        return True, "ready"
    except Exception as exc:
        return False, f"Docker check failed: {exc}"


def _check_local() -> tuple[bool, str]:
    allow = os.environ.get("VENGINE_ALLOW_LOCAL_RUNNER", "").strip().lower()
    developer = os.environ.get("VENGINE_DEV_MODE", "").strip().lower()
    if allow in {"1", "true", "yes", "on"} and developer in {"1", "true", "yes", "on"}:
        return True, "ready (developer-only host execution)"
    return False, "Host execution disabled; container isolation is required."


def available_runners() -> dict[str, dict[str, Any]]:
    podman_ok, podman_msg = _check_podman()
    docker_ok, docker_msg = _check_docker()
    local_ok, local_msg = _check_local()
    return {
        "podman": {"available": podman_ok, "message": podman_msg},
        "docker": {"available": docker_ok, "message": docker_msg},
        "local": {"available": local_ok, "message": local_msg},
    }


def active_backend() -> str | None:
    runners = available_runners()
    if runners["podman"]["available"]:
        return "podman"
    if runners["docker"]["available"]:
        return "docker"
    if runners["local"]["available"]:
        return "local"
    return None


def available() -> tuple[bool, str]:
    backend = active_backend()
    if backend == "podman":
        return True, "ready (podman+gvisor)"
    if backend == "docker":
        return True, "ready (docker)"
    if backend == "local":
        return True, "ready (local-dev)"
    return False, "No code sandbox ready. Install rootless Podman+runsc or Docker with runner images."


def _run_podman(spec: CodeSpec | SQLSpec, response: Any) -> GradeResult:
    language = spec.language if isinstance(spec, CodeSpec) else "sql"
    worker = WORKERS / ("node_worker.js" if language == "javascript" else "python_worker.py")
    image = NODE_IMAGE if language == "javascript" else PYTHON_IMAGE
    command = ["podman", "run", "--rm", "--interactive", "--pull=never", "--runtime=runsc",
               "--network=none", "--read-only", "--cap-drop=all", "--security-opt=no-new-privileges",
               "--memory=128m", "--cpus=1", "--pids-limit=32", "--user=65534:65534",
               "--tmpfs=/tmp:rw,noexec,nosuid,size=16m", "--mount",
               f"type=bind,src={worker},dst=/worker,ro=true", image]
    command += ["node", "/worker"] if language == "javascript" else ["python", "-I", "/worker"]
    payload = {"spec": spec.model_dump(mode="json"), "response": response}
    try:
        result = subprocess.run(command, input=json.dumps(payload), capture_output=True,
                                text=True, timeout=12, check=False)
    except (subprocess.TimeoutExpired, OSError) as exc:
        return GradeResult(outcome="error", feedback=f"Runner failed: {type(exc).__name__}")
    if result.returncode:
        return GradeResult(outcome="error", feedback="Sandbox could not run. Check image availability and runtime.")
    try:
        data = json.loads(result.stdout)
        return GradeResult.model_validate(data)
    except (ValueError, TypeError):
        return GradeResult(outcome="error", feedback="Sandbox returned an invalid result.")


def _run_docker(spec: CodeSpec | SQLSpec, response: Any) -> GradeResult:
    language = spec.language if isinstance(spec, CodeSpec) else "sql"
    worker = WORKERS / ("node_worker.js" if language == "javascript" else "python_worker.py")
    image = NODE_IMAGE if language == "javascript" else PYTHON_IMAGE
    command = ["docker", "run", "--rm", "--interactive", "--pull=never",
               "--network=none", "--read-only", "--cap-drop=all", "--security-opt=no-new-privileges",
               "--memory=128m", "--cpus=1", "--pids-limit=32", "--user=65534:65534",
               "--tmpfs=/tmp:rw,noexec,nosuid,size=16m", "--mount",
               f"type=bind,src={worker},dst=/worker,ro=true", image]
    command += ["node", "/worker"] if language == "javascript" else ["python", "-I", "/worker"]
    payload = {"spec": spec.model_dump(mode="json"), "response": response}
    try:
        result = subprocess.run(command, input=json.dumps(payload), capture_output=True,
                                text=True, timeout=12, check=False)
    except (subprocess.TimeoutExpired, OSError) as exc:
        return GradeResult(outcome="error", feedback=f"Docker runner failed: {type(exc).__name__}")
    if result.returncode:
        return GradeResult(outcome="error", feedback="Docker sandbox failed. Check image availability.")
    try:
        data = json.loads(result.stdout)
        return GradeResult.model_validate(data)
    except (ValueError, TypeError):
        return GradeResult(outcome="error", feedback="Sandbox returned an invalid result.")


def _run_local(spec: CodeSpec | SQLSpec, response: Any) -> GradeResult:
    language = spec.language if isinstance(spec, CodeSpec) else "sql"
    worker = WORKERS / ("node_worker.js" if language == "javascript" else "python_worker.py")
    executable = shutil.which("node") if language == "javascript" else sys.executable
    if not executable:
        return GradeResult(outcome="error", feedback=f"Runtime executable for {language} not found")
    payload = {"spec": spec.model_dump(mode="json"), "response": response}

    def preexec():
        try:
            import resource
            resource.setrlimit(resource.RLIMIT_AS, (512 * 1024 * 1024, 512 * 1024 * 1024))
            resource.setrlimit(resource.RLIMIT_CPU, (5, 5))
        except Exception:
            pass

    try:
        result = subprocess.run(
            [executable, str(worker)],
            input=json.dumps(payload),
            capture_output=True,
            text=True,
            timeout=8,
            preexec_fn=preexec if os.name == "posix" else None,
            check=False,
        )
    except subprocess.TimeoutExpired:
        return GradeResult(outcome="error", feedback="Execution timed out (limit: 8s)")
    except Exception as exc:
        return GradeResult(outcome="error", feedback=f"Local runner failed: {type(exc).__name__}")

    try:
        data = json.loads(result.stdout)
        return GradeResult.model_validate(data)
    except Exception:
        err = result.stderr.strip()[:200] if result.stderr else "Invalid output from worker"
        return GradeResult(outcome="error", feedback=f"Worker error: {err}")


def run_code(spec: CodeSpec | SQLSpec, response: Any) -> GradeResult:
    backend = active_backend()
    if backend is None:
        _, reason = available()
        return GradeResult(outcome="error", feedback=reason)
    if not isinstance(response, str) or len(response) > 200_000:
        return GradeResult(outcome="error", feedback="Code must be text under 200 KB.")
    if backend == "local":
        return _run_local(spec, response)
    if backend == "docker":
        return _run_docker(spec, response)
    return _run_podman(spec, response)
