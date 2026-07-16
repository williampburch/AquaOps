from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path


def test_postgres_backup_targets_named_database_and_refuses_overwrite(tmp_path: Path) -> None:
    root, env, call_log = _operation_fixture(tmp_path)
    output = tmp_path / "aquaops.dump"

    result = subprocess.run(
        [str(root / "scripts" / "postgres-backup.sh"), str(output)],
        cwd=root,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert output.read_text() == "postgres-dump"
    assert "database=aquaops" in result.stdout
    assert "exec -T db pg_dump -U aquaops -d aquaops --format=custom" in call_log.read_text()

    repeated = subprocess.run(
        [str(root / "scripts" / "postgres-backup.sh"), str(output)],
        cwd=root,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    assert repeated.returncode == 1
    assert "Refusing to overwrite" in repeated.stderr


def test_postgres_restore_requires_exact_database_confirmation(tmp_path: Path) -> None:
    root, env, call_log = _operation_fixture(tmp_path)
    dump = tmp_path / "aquaops.dump"
    dump.write_text("postgres-dump")

    result = subprocess.run(
        [
            str(root / "scripts" / "postgres-restore.sh"),
            str(dump),
            "--confirm-db",
            "wrong_database",
        ],
        cwd=root,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 1
    assert "does not match configured database aquaops" in result.stderr
    assert not call_log.exists()


def test_postgres_restore_accepts_only_an_empty_database(tmp_path: Path) -> None:
    root, env, call_log = _operation_fixture(tmp_path)
    dump = tmp_path / "aquaops.dump"
    dump.write_text("postgres-dump")

    result = subprocess.run(
        [
            str(root / "scripts" / "postgres-restore.sh"),
            str(dump),
            "--confirm-db",
            "aquaops",
        ],
        cwd=root,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    calls = call_log.read_text()
    assert "exec -T db psql -U aquaops -d aquaops -Atqc" in calls
    assert "exec -T db pg_restore -U aquaops -d aquaops" in calls


def _operation_fixture(tmp_path: Path) -> tuple[Path, dict[str, str], Path]:
    project_root = Path(__file__).resolve().parents[2]
    root = tmp_path / "aquaops"
    scripts = root / "scripts"
    scripts.mkdir(parents=True)
    for name in ("postgres-backup.sh", "postgres-restore.sh"):
        shutil.copy2(project_root / "scripts" / name, scripts / name)
    (root / ".env").write_text("POSTGRES_DB=aquaops\nPOSTGRES_USER=aquaops\n")

    call_log = tmp_path / "calls.log"
    fake_bin = tmp_path / "bin"
    fake_bin.mkdir()
    docker = fake_bin / "docker"
    docker.write_text(
        """#!/usr/bin/env bash
printf 'docker %s\\n' "$*" >> "$CALL_LOG"
if [[ "$*" == *" psql "* ]]; then
  printf '0\\n'
elif [[ "$*" == *" pg_dump "* ]]; then
  printf 'postgres-dump'
elif [[ "$*" == *" pg_restore "* ]]; then
  cat >/dev/null
fi
"""
    )
    docker.chmod(0o755)

    env = os.environ.copy()
    env["PATH"] = f"{fake_bin}:{env['PATH']}"
    env["CALL_LOG"] = str(call_log)
    return root, env, call_log
