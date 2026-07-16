from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path


def test_image_deploy_pulls_migrates_and_never_builds(tmp_path: Path) -> None:
    deploy_root, call_log, env = _deployment_fixture(tmp_path, health_mode="pass")
    env["AQUAOPS_IMAGE_TAG"] = "abc1234"

    result = subprocess.run(
        [str(deploy_root / "scripts" / "deploy-image.sh")],
        cwd=deploy_root,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    calls = call_log.read_text()
    assert "docker pull ghcr.io/williampburch/aquaops:abc1234" in calls
    assert "compose -f docker-compose.prod.yml up -d --no-build db" in calls
    assert "compose -f docker-compose.prod.yml exec -T db sh -c" in calls
    assert "run --rm web alembic upgrade head" in calls
    assert "up -d --no-build --force-recreate --remove-orphans web" in calls
    assert " build " not in f" {calls} "
    assert calls.index("up -d --no-build db") < calls.index("run --rm web alembic upgrade head")


def test_image_deploy_rolls_back_previous_image_after_failed_health(
    tmp_path: Path,
) -> None:
    deploy_root, call_log, env = _deployment_fixture(tmp_path, health_mode="fail-once")
    env["AQUAOPS_IMAGE_TAG"] = "badcafe"

    result = subprocess.run(
        [str(deploy_root / "scripts" / "deploy-image.sh")],
        cwd=deploy_root,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 1
    assert "Health check failed" in result.stderr
    assert "Rollback succeeded" in result.stderr
    calls = call_log.read_text()
    assert "docker image tag sha256:previous ghcr.io/williampburch/aquaops:rollback-" in calls
    assert calls.count("up -d --no-build --force-recreate --remove-orphans web") == 2


def _deployment_fixture(
    tmp_path: Path,
    *,
    health_mode: str,
) -> tuple[Path, Path, dict[str, str]]:
    project_root = Path(__file__).resolve().parents[2]
    deploy_root = tmp_path / "aquaops"
    scripts_dir = deploy_root / "scripts"
    scripts_dir.mkdir(parents=True)
    shutil.copy2(project_root / "scripts" / "deploy-image.sh", scripts_dir)
    shutil.copy2(project_root / "docker-compose.prod.yml", deploy_root)
    (deploy_root / ".env").write_text("APP_ENV=production\n")

    call_log = tmp_path / "calls.log"
    fake_bin = tmp_path / "bin"
    fake_bin.mkdir()
    _write_executable(
        fake_bin / "docker",
        """#!/usr/bin/env bash
printf 'docker %s\\n' "$*" >> "$CALL_LOG"
if [[ "$1" == "inspect" && "$*" == *"{{.Image}}"* ]]; then
  printf 'sha256:previous\\n'
elif [[ "$1" == "inspect" && "$*" == *"{{.Config.Image}}"* ]]; then
  printf 'aquaops-web:previous\\n'
fi
exit 0
""",
    )
    _write_executable(
        fake_bin / "curl",
        """#!/usr/bin/env bash
printf 'curl %s\\n' "$*" >> "$CALL_LOG"
if [[ "$HEALTH_MODE" == "fail-once" && ! -f "$HEALTH_STATE" ]]; then
  : > "$HEALTH_STATE"
  exit 1
fi
exit 0
""",
    )
    _write_executable(fake_bin / "flock", "#!/usr/bin/env bash\nexit 0\n")
    _write_executable(fake_bin / "sleep", "#!/usr/bin/env bash\nexit 0\n")

    env = os.environ.copy()
    env.update(
        {
            "PATH": f"{fake_bin}:{env['PATH']}",
            "CALL_LOG": str(call_log),
            "HEALTH_MODE": health_mode,
            "HEALTH_STATE": str(tmp_path / "health-state"),
            "AQUAOPS_HEALTH_ATTEMPTS": "1",
            "AQUAOPS_HEALTH_DELAY_SECONDS": "0",
            "AQUAOPS_DEPLOY_LOCK_FILE": str(tmp_path / "deploy.lock"),
        }
    )
    return deploy_root, call_log, env


def _write_executable(path: Path, content: str) -> None:
    path.write_text(content)
    path.chmod(0o755)
