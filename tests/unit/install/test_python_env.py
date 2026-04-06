from __future__ import annotations

from odylith.install.python_env import scrubbed_python_env


def test_scrubbed_python_env_removes_consumer_python_state_and_keeps_path() -> None:
    env = scrubbed_python_env(
        {
            "PATH": "/usr/bin:/bin",
            "VIRTUAL_ENV": "/tmp/consumer-venv",
            "CONDA_PREFIX": "/tmp/conda",
            "CONDA_DEFAULT_ENV": "consumer",
            "PDM_PYTHON": "/tmp/pdm-python",
            "PEX_PYTHON": "/tmp/pex-python",
            "PEX_PYTHON_PATH": "/tmp/pex-path",
            "PIPENV_ACTIVE": "1",
            "POETRY_ACTIVE": "1",
            "PYTHONHOME": "/tmp/python-home",
            "PYTHONEXECUTABLE": "/tmp/python-executable",
            "__PYVENV_LAUNCHER__": "/tmp/launcher",
            "PYTHONPATH": "/tmp/consumer-src",
            "PYENV_VERSION": "3.11.9",
            "UV_PROJECT_ENVIRONMENT": "/tmp/uv-env",
            "UV_PYTHON": "/tmp/uv-python",
            "KEEP_ME": "yes",
        }
    )

    assert env["PATH"] == "/usr/bin:/bin"
    assert env["KEEP_ME"] == "yes"
    assert env["PYTHONNOUSERSITE"] == "1"
    assert "VIRTUAL_ENV" not in env
    assert "CONDA_PREFIX" not in env
    assert "CONDA_DEFAULT_ENV" not in env
    assert "PDM_PYTHON" not in env
    assert "PEX_PYTHON" not in env
    assert "PEX_PYTHON_PATH" not in env
    assert "PIPENV_ACTIVE" not in env
    assert "POETRY_ACTIVE" not in env
    assert "PYTHONHOME" not in env
    assert "PYTHONEXECUTABLE" not in env
    assert "__PYVENV_LAUNCHER__" not in env
    assert "PYTHONPATH" not in env
    assert "PYENV_VERSION" not in env
    assert "UV_PROJECT_ENVIRONMENT" not in env
    assert "UV_PYTHON" not in env
