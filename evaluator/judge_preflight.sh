#!/usr/bin/env bash

set +e
set +u
set +o pipefail

IMAGE="ghcr.io/xaltezzarx/boneqc-c7@sha256:d67b6a3c695a0cd495e5fd7c31e4d5f2142d13452afec4e304e2f01c9fc045d7"
DIGEST="sha256:d67b6a3c695a0cd495e5fd7c31e4d5f2142d13452afec4e304e2f01c9fc045d7"

FAIL=0
WARN=0

pass() {
    echo "PASS | $*"
}

warn() {
    echo "WARN | $*"
    WARN=$((WARN + 1))
}

fail() {
    echo "FAIL | $*"
    FAIL=$((FAIL + 1))
}

echo "============================================================"
echo "BoneQC LCT 2026 — Judge Environment Preflight"
echo "============================================================"

echo
echo "===== 1. HOST ====="

OS="$(uname -s 2>/dev/null)"
ARCH="$(uname -m 2>/dev/null)"

echo "OS=$OS"
echo "ARCH=$ARCH"

if [ "$OS" = "Linux" ]; then
    pass "Linux host"
else
    fail "Linux host required"
fi

case "$ARCH" in
    x86_64|amd64)
        pass "x86_64 architecture"
        ;;
    *)
        fail "x86_64 architecture required"
        ;;
esac

echo
echo "===== 2. REQUIRED COMMANDS ====="

for CMD in \
    python3 \
    docker \
    nvidia-smi
do
    if command -v "$CMD" >/dev/null 2>&1; then
        pass "$CMD available"
    else
        fail "$CMD missing"
    fi
done

echo
echo "===== 3. PYTHON ====="

if command -v python3 >/dev/null 2>&1; then
    python3 --version

    python3 - <<'PY'
import sys

ok = sys.version_info >= (3, 10)

print(
    "PYTHON_VERSION_SUPPORTED="
    + ("PASS" if ok else "FAIL")
)

raise SystemExit(
    0 if ok else 20
)
PY

    if [ "$?" -eq 0 ]; then
        pass "host Python >= 3.10"
    else
        fail "host Python >= 3.10 required"
    fi
fi

echo
echo "===== 4. DOCKER ====="

if command -v docker >/dev/null 2>&1; then
    docker version \
      --format \
      'DOCKER_SERVER_VERSION={{.Server.Version}}'

    if docker info >/dev/null 2>&1; then
        pass "Docker daemon reachable"
    else
        fail "Docker daemon unavailable"
    fi
fi

echo
echo "===== 5. DISK ====="

FREE_KB="$(
  df -Pk . 2>/dev/null \
  | awk 'NR==2 {print $4}'
)"

if echo "$FREE_KB" \
  | grep -Eq '^[0-9]+$'
then
    FREE_GIB=$(( FREE_KB / 1024 / 1024 ))

    echo "FREE_DISK_GIB=$FREE_GIB"

    if [ "$FREE_GIB" -ge 20 ]; then
        pass "recommended free disk >= 20 GiB"
    elif [ "$FREE_GIB" -ge 8 ]; then
        warn "less than recommended 20 GiB free"
    else
        fail "insufficient free disk"
    fi
else
    warn "unable to determine free disk"
fi

echo
echo "===== 6. NVIDIA HOST ====="

if command -v nvidia-smi >/dev/null 2>&1; then
    nvidia-smi \
      --query-gpu=name,driver_version,memory.total \
      --format=csv,noheader

    NVIDIA_EXIT=$?

    if [ "$NVIDIA_EXIT" -eq 0 ]; then
        pass "NVIDIA driver / GPU visible"
    else
        fail "NVIDIA GPU not available"
    fi
fi

echo
echo "===== 7. IMMUTABLE C7 IMAGE ====="

if ! docker image inspect "$IMAGE" >/dev/null 2>&1; then
    echo "C7_IMAGE_LOCAL=NO"
    echo "Pulling exact immutable image..."

    docker pull "$IMAGE"

    if [ "$?" -ne 0 ]; then
        fail "unable to pull immutable C7 image"
    fi
else
    echo "C7_IMAGE_LOCAL=YES"
fi

if docker image inspect "$IMAGE" >/dev/null 2>&1; then
    REPO_DIGESTS="$(
      docker image inspect "$IMAGE" \
        --format '{{json .RepoDigests}}'
    )"

    echo "REPO_DIGESTS=$REPO_DIGESTS"

    if echo "$REPO_DIGESTS" \
      | grep -Fq "$DIGEST"
    then
        pass "immutable C7 manifest digest verified"
    else
        fail "immutable C7 digest mismatch"
    fi
fi

echo
echo "===== 8. NVIDIA CONTAINER TOOLKIT + CUDA ====="

if docker image inspect "$IMAGE" >/dev/null 2>&1; then
    GPU_REPORT="$(
      docker run \
        --rm \
        --network none \
        --gpus all \
        --entrypoint python \
        "$IMAGE" \
        -c '
import importlib.util
import torch

print(
    "TORCH_VERSION="
    + str(torch.__version__)
)

print(
    "TORCH_CUDA_BUILD="
    + str(torch.version.cuda)
)

available = torch.cuda.is_available()

print(
    "CUDA_AVAILABLE="
    + str(available)
)

if not available:
    raise SystemExit(20)

name = torch.cuda.get_device_name(0)
major, minor = torch.cuda.get_device_capability(0)

target = f"sm_{major}{minor}"
arches = torch.cuda.get_arch_list()

print(
    "GPU_NAME="
    + name
)

print(
    "GPU_COMPUTE_CAPABILITY="
    + f"{major}.{minor}"
)

print(
    "GPU_TARGET_ARCH="
    + target
)

print(
    "TORCH_COMPILED_ARCHES="
    + ",".join(arches)
)

supported = target in arches

print(
    "CURRENT_GPU_ARCH_SUPPORTED="
    + str(supported)
)

for module in (
    "pydicom",
    "pandas",
    "openpyxl",
):
    print(
        module.upper()
        + "="
        + (
            "AVAILABLE"
            if importlib.util.find_spec(module)
            else "MISSING"
        )
    )

raise SystemExit(
    0 if supported else 21
)
' 2>&1
    )"

    GPU_EXIT=$?

    echo "$GPU_REPORT"

    if [ "$GPU_EXIT" -eq 0 ]; then
        pass "NVIDIA Container Toolkit / CUDA runtime"
        pass "current GPU architecture is compiled into C7 runtime"
    else
        fail "GPU container preflight"
    fi
fi

echo
echo "===== 9. EVALUATOR ====="

if [ -f evaluator/boneqc_evaluator.py ]; then

    python3 -m py_compile \
      evaluator/boneqc_evaluator.py

    if [ "$?" -eq 0 ]; then
        pass "evaluator Python syntax"
    else
        fail "evaluator Python syntax"
    fi

    python3 \
      evaluator/boneqc_evaluator.py \
      --help \
      >/dev/null

    if [ "$?" -eq 0 ]; then
        pass "evaluator CLI"
    else
        fail "evaluator CLI"
    fi

    if grep -n -A35 \
      '^def run_c7' \
      evaluator/boneqc_evaluator.py \
      | grep -q '"none"'
    then
        pass "C7 inference network isolation present"
    else
        fail "C7 inference network isolation missing"
    fi

else
    fail "evaluator/boneqc_evaluator.py missing"
fi

echo
echo "===== 10. QUICKSTART ====="

echo "Run:"
echo
echo "  python3 evaluator/boneqc_evaluator.py INPUT.zip OUTPUT_DIR"
echo
echo "Expected primary outputs:"
echo
echo "  OUTPUT_DIR/boneqc-c7-results-v1.csv"
echo "  OUTPUT_DIR/boneqc-c7-results-v1.xlsx"
echo "  OUTPUT_DIR/boneqc-evaluator-manifest-v1.json"
echo "  OUTPUT_DIR/boneqc-evaluator-audit-v1.json"

echo
echo "===== FINAL ====="

echo "WARNINGS=$WARN"
echo "FAILURES=$FAIL"

if [ "$FAIL" -eq 0 ]; then
    echo "BONEQC_JUDGE_PREFLIGHT=PASS"
    exit 0
fi

echo "BONEQC_JUDGE_PREFLIGHT=FAIL"
exit 1
