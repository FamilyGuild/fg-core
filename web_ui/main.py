"""Runtime entry point for the FamilyGuild NiceGUI shell."""

from __future__ import annotations

import argparse
import os
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path

import dbzero as db0
from nicegui import app, ui
from nicegui.storage import Storage

from fg_core.queries import get_app_state
from web_ui.shell import build_shell

DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8090
DEFAULT_STATE_DIR = Path("app-data")
STORAGE_SECRET_ENV = "FG_STORAGE_SECRET"


@dataclass(frozen=True)
class RuntimeConfig:
    """Deployment settings kept outside persisted household preferences."""

    state_dir: Path
    host: str
    port: int
    storage_secret: str


def parse_runtime_config(
    argv: Sequence[str] | None = None,
    environ: Mapping[str, str] | None = None,
) -> RuntimeConfig:
    """Parse command-line settings and the required browser-storage secret."""

    parser = argparse.ArgumentParser(description="Run the FamilyGuild Core web shell.")
    parser.add_argument("--state-dir", type=Path, default=DEFAULT_STATE_DIR)
    parser.add_argument("--host", default=DEFAULT_HOST)
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    arguments = parser.parse_args(argv)

    environment = os.environ if environ is None else environ
    storage_secret = environment.get(STORAGE_SECRET_ENV, "").strip()
    if not storage_secret:
        parser.error(f"{STORAGE_SECRET_ENV} must contain a non-empty storage secret")

    return RuntimeConfig(
        state_dir=arguments.state_dir.expanduser().resolve(),
        host=arguments.host,
        port=arguments.port,
        storage_secret=storage_secret,
    )


def run(config: RuntimeConfig) -> None:
    """Open core state and run the NiceGUI server until shutdown."""

    config.state_dir.mkdir(parents=True, exist_ok=True)
    Storage.path = (config.state_dir / "nicegui").resolve()
    db0.init(str(config.state_dir / "dbzero"), prefix="core")
    state_closed = False

    def close_state() -> None:
        nonlocal state_closed
        if not state_closed:
            db0.close()
            state_closed = True

    try:
        # Uvicorn can replay SIGTERM before ui.run returns, bypassing finally.
        app.on_shutdown(close_state)
        ui.run(
            root=lambda: build_shell(get_app_state()),
            host=config.host,
            port=config.port,
            title="FamilyGuild",
            storage_secret=config.storage_secret,
            reload=False,
            show=False,
        )
    finally:
        close_state()


def main() -> None:
    """Run the web shell from command-line configuration."""

    run(parse_runtime_config())


if __name__ in {"__main__", "__mp_main__"}:
    main()
