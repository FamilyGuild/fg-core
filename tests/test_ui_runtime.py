import os
import signal
import socket
import subprocess
import sys
import time
from collections.abc import Callable
from pathlib import Path
from textwrap import dedent
from types import SimpleNamespace

import pytest
from nicegui import app

import web_ui.main as main
from web_ui.main import DEFAULT_HOST, DEFAULT_PORT, RuntimeConfig, parse_runtime_config


def test_runtime_defaults_to_local_port_8090(tmp_path: Path) -> None:
    config = parse_runtime_config(
        ["--state-dir", str(tmp_path)],
        {"FG_STORAGE_SECRET": "test-secret"},
    )

    assert config.host == DEFAULT_HOST == "127.0.0.1"
    assert config.port == DEFAULT_PORT == 8090
    assert config.state_dir == tmp_path.resolve()
    assert config.storage_secret == "test-secret"


def test_runtime_host_and_port_are_configurable(tmp_path: Path) -> None:
    config = parse_runtime_config(
        ["--state-dir", str(tmp_path), "--host", "0.0.0.0", "--port", "8099"],
        {"FG_STORAGE_SECRET": "test-secret"},
    )

    assert config.host == "0.0.0.0"
    assert config.port == 8099


def test_runtime_requires_storage_secret(tmp_path: Path) -> None:
    with pytest.raises(SystemExit):
        parse_runtime_config(["--state-dir", str(tmp_path)], {})


def test_run_configures_state_lifecycle_and_nicegui(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls: list[tuple[str, object]] = []
    storage = SimpleNamespace(path=None)
    config = RuntimeConfig(tmp_path, "127.0.0.1", 8090, "test-secret")

    monkeypatch.setattr(main, "Storage", storage)
    monkeypatch.setattr(app, "on_shutdown", lambda handler: None)
    monkeypatch.setattr(
        main.db0,
        "init",
        lambda path, prefix: calls.append(("init", (path, prefix))),
    )
    monkeypatch.setattr(main.db0, "close", lambda: calls.append(("close", None)))
    monkeypatch.setattr(main.ui, "run", lambda **kwargs: calls.append(("run", kwargs)))

    main.run(config)

    assert calls[0] == ("init", (str(tmp_path / "dbzero"), "core"))
    assert calls[-1] == ("close", None)
    run_settings = calls[1][1]
    assert isinstance(run_settings, dict)
    assert run_settings["host"] == "127.0.0.1"
    assert run_settings["port"] == 8090
    assert run_settings["storage_secret"] == "test-secret"
    assert run_settings["reload"] is False
    assert storage.path == (tmp_path / "nicegui").resolve()


@pytest.mark.parametrize("startup_failure", [False, True])
def test_run_closes_state_once_on_shutdown_or_startup_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, startup_failure: bool
) -> None:
    shutdown_handlers: list[Callable[[], None]] = []
    close_calls: list[bool] = []
    monkeypatch.setattr(main.db0, "init", lambda *args, **kwargs: None)
    monkeypatch.setattr(main.db0, "close", lambda: close_calls.append(True))
    monkeypatch.setattr(app, "on_shutdown", shutdown_handlers.append)
    monkeypatch.setattr(main, "Storage", SimpleNamespace(path=None))

    def run_server(**kwargs: object) -> None:
        if startup_failure:
            raise RuntimeError("startup failed")
        assert len(shutdown_handlers) == 1
        shutdown_handlers[0]()
        assert close_calls == [True]

    monkeypatch.setattr(main.ui, "run", run_server)
    config = RuntimeConfig(tmp_path, "127.0.0.1", 8090, "test-secret")
    if startup_failure:
        with pytest.raises(RuntimeError, match="startup failed"):
            main.run(config)
    else:
        main.run(config)
    assert close_calls == [True]


def test_sigterm_shutdown_persists_pending_household_state(tmp_path: Path) -> None:
    """Exercise real server shutdown before dbzero's next autocommit."""

    ready_path = tmp_path / "ready"
    server_code = dedent("""\
        import asyncio
        import sys
        from pathlib import Path
        from typing import Any

        import dbzero as db0
        from nicegui import app

        from fg_core.commands import add_parent_member, create_family
        from web_ui.main import RuntimeConfig, run

        original_init = db0.init

        def init_with_pending_writes(path: str, **kwargs: Any) -> None:
            original_init(path, autocommit_interval=60000, **kwargs)

        db0.init = init_with_pending_writes

        def prepare_household() -> None:
            state = create_family("Shutdown household")
            add_parent_member(state, "Parent")

        async def prepare_on_startup() -> None:
            await asyncio.to_thread(prepare_household)
            Path(sys.argv[2]).write_text("ready")

        app.on_startup(prepare_on_startup)
        run(RuntimeConfig(Path(sys.argv[1]), "127.0.0.1", int(sys.argv[3]), "test-secret"))
        """)
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        port = listener.getsockname()[1]
    process = subprocess.Popen(
        [sys.executable, "-c", server_code, str(tmp_path), str(ready_path), str(port)],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        env={
            key: value
            for key, value in os.environ.items()
            if key not in {"PYTEST_CURRENT_TEST", "NICEGUI_USER_SIMULATION"}
        },
    )
    try:
        deadline = time.monotonic() + 15
        while not ready_path.exists() and process.poll() is None and time.monotonic() < deadline:
            time.sleep(0.01)
        if not ready_path.exists():
            if process.poll() is None:
                process.kill()
            output, _ = process.communicate(timeout=5)
            pytest.fail(f"server did not prepare the household:\n{output}")
        process.send_signal(signal.SIGTERM)
        output, _ = process.communicate(timeout=15)
        assert process.returncode in {0, -signal.SIGTERM}, output
    finally:
        if process.poll() is None:
            process.kill()
        process.communicate(timeout=5)

    readback_code = dedent("""\
        import sys
        import dbzero as db0
        from fg_core.models import FamilyGuildAppState

        db0.init(sys.argv[1], prefix="core", read_write=False)
        try:
            states = list(db0.find(FamilyGuildAppState))
            assert len(states) == 1, "pending household was lost"
            state = states[0]
            assert state.preferences.family_display_name == "Shutdown household"
            assert len(state.family.members) == 1
            assert state.family.members[0].display_name == "Parent"
        finally:
            db0.close()
        """)
    readback = subprocess.run(
        [sys.executable, "-c", readback_code, str(tmp_path / "dbzero")],
        capture_output=True,
        text=True,
        timeout=15,
    )
    assert readback.returncode == 0, readback.stdout + readback.stderr
