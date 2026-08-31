#!/usr/bin/env bash
set -euo pipefail

need_cmd() {
  if ! command -v "$1" >/dev/null 2>&1; then
    echo "missing required command: $1" >&2
    exit 1
  fi
}

echo "[preflight] checking WSL2/Linux environment"
if [[ -f /proc/sys/kernel/osrelease ]] && grep -qiE "microsoft|wsl" /proc/sys/kernel/osrelease; then
  echo "[ok] running under WSL-compatible kernel: $(cat /proc/sys/kernel/osrelease)"
else
  echo "[warn] WSL marker not found; continuing because native Linux can also run this sandbox"
fi

need_cmd docker
need_cmd kubectl
need_cmd kind
need_cmd helm
need_cmd python3

echo "[preflight] checking Docker"
docker info >/dev/null
docker compose version

if [[ "${SKIP_HELLO_WORLD:-0}" != "1" ]]; then
  docker run --rm hello-world >/dev/null
  echo "[ok] docker hello-world passed"
else
  echo "[skip] docker hello-world skipped because SKIP_HELLO_WORLD=1"
fi

echo "[preflight] checking Kubernetes tooling"
kind version
kubectl version --client=true
helm version --short

echo "[preflight] checking Python dependencies"
python3 - <<'PY'
import sys
try:
    import yaml
except Exception as exc:
    print("missing Python dependency PyYAML; install with: python3 -m pip install PyYAML", file=sys.stderr)
    raise SystemExit(1) from exc
print(f"[ok] python={sys.version.split()[0]} pyyaml={yaml.__version__}")
PY

echo "[preflight] all required tools are available"
