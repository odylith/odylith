from __future__ import annotations

import os
from typing import Mapping

PYTHON_ENV_SCRUB_KEYS: tuple[str, ...] = (
    "VIRTUAL_ENV",
    "CONDA_PREFIX",
    "CONDA_DEFAULT_ENV",
    "PDM_PYTHON",
    "PEX_PYTHON",
    "PEX_PYTHON_PATH",
    "PIPENV_ACTIVE",
    "POETRY_ACTIVE",
    "PYTHONHOME",
    "PYTHONEXECUTABLE",
    "__PYVENV_LAUNCHER__",
    "PYTHONPATH",
    "PYENV_VERSION",
    "UV_PROJECT_ENVIRONMENT",
    "UV_PYTHON",
)

PYTHON_ENV_SCRUB_LINES: tuple[str, ...] = (
    "unset VIRTUAL_ENV",
    "unset CONDA_PREFIX",
    "unset CONDA_DEFAULT_ENV",
    "unset PDM_PYTHON",
    "unset PEX_PYTHON",
    "unset PEX_PYTHON_PATH",
    "unset PIPENV_ACTIVE",
    "unset POETRY_ACTIVE",
    "unset PYTHONHOME",
    "unset PYTHONEXECUTABLE",
    "unset __PYVENV_LAUNCHER__",
    "unset PYTHONPATH",
    "unset PYENV_VERSION",
    "unset UV_PROJECT_ENVIRONMENT",
    "unset UV_PYTHON",
    "export PYTHONNOUSERSITE=1",
)


def scrubbed_python_env(
    env: Mapping[str, str] | None = None,
    *,
    extra: Mapping[str, str] | None = None,
) -> dict[str, str]:
    payload = dict(os.environ if env is None else env)
    for key in PYTHON_ENV_SCRUB_KEYS:
        payload.pop(key, None)
    payload["PYTHONNOUSERSITE"] = "1"
    if extra:
        payload.update({str(key): str(value) for key, value in extra.items()})
    return payload
