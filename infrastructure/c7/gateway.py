from __future__ import annotations

from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import csv
import fcntl
import hashlib
import hmac
import json
import os
import subprocess
import tempfile
import threading
import time


HOST = os.environ.get(
    "BONEQC_GATEWAY_HOST",
    "127.0.0.1",
)

PORT = int(
    os.environ.get(
        "BONEQC_GATEWAY_PORT",
        "18180",
    )
)

IMAGE = os.environ.get(
    "BONEQC_C7_IMAGE",
    "boneqc-c7-final:runtime-v1",
)

TOKEN_FILE = Path(
    os.environ.get(
        "BONEQC_GATEWAY_TOKEN_FILE",
        str(
            Path.home()
            / ".config/boneqc/c7-gateway.token"
        ),
    )
)

MAX_BODY_BYTES = int(
    os.environ.get(
        "BONEQC_GATEWAY_MAX_BODY_BYTES",
        str(256 * 1024 * 1024),
    )
)

TIMEOUT_SECONDS = int(
    os.environ.get(
        "BONEQC_GATEWAY_TIMEOUT_SECONDS",
        "3600",
    )
)

GPU_GUARD_ENABLED = (
    os.environ.get(
        "BONEQC_GPU_GUARD_ENABLED",
        "false",
    ).strip().lower()
    in {
        "1",
        "true",
        "yes",
        "on",
    }
)

GPU_LOCK_FILE = Path(
    os.environ.get(
        "BONEQC_GPU_LOCK_FILE",
        "/run/boneqc-gpu/gtx1060.lock",
    )
)

GPU_PRIORITY_FILE = Path(
    os.environ.get(
        "BONEQC_GPU_PRIORITY_FILE",
        "/run/boneqc-gpu/boneqc-priority",
    )
)

GPU_LOCK_TIMEOUT_SECONDS = float(
    os.environ.get(
        "BONEQC_GPU_LOCK_TIMEOUT_SECONDS",
        "120",
    )
)

GPU_MIN_FREE_MIB = int(
    os.environ.get(
        "BONEQC_GPU_MIN_FREE_MIB",
        "3072",
    )
)

JOB_LOCK = threading.Lock()


class GPUResourceBusyError(RuntimeError):
    pass


def initialize_gpu_guard() -> None:
    if not GPU_GUARD_ENABLED:
        return

    GPU_LOCK_FILE.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    # A previous hard crash must not leave
    # BoneQC permanently marked as waiting.
    try:
        GPU_PRIORITY_FILE.unlink(
            missing_ok=True
        )
    except OSError:
        pass


def gpu_free_mib() -> int:
    try:
        result = subprocess.run(
            [
                "nvidia-smi",
                "--query-gpu=memory.free",
                "--format=csv,noheader,nounits",
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=5,
            check=False,
        )

    except (
        OSError,
        subprocess.TimeoutExpired,
    ) as exc:
        raise GPUResourceBusyError(
            "GPU telemetry unavailable"
        ) from exc

    if result.returncode != 0:
        raise GPUResourceBusyError(
            "GPU telemetry unavailable"
        )

    values = [
        line.strip()
        for line in result.stdout.splitlines()
        if line.strip()
    ]

    if not values:
        raise GPUResourceBusyError(
            "GPU memory telemetry missing"
        )

    try:
        return int(
            values[0].split()[0]
        )

    except (
        TypeError,
        ValueError,
        IndexError,
    ) as exc:
        raise GPUResourceBusyError(
            "GPU memory telemetry invalid"
        ) from exc


def acquire_gpu_guard():
    if not GPU_GUARD_ENABLED:
        return None

    GPU_LOCK_FILE.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    priority_payload = {
        "owner": "boneqc",
        "pid": os.getpid(),
        "created_unix": time.time(),
    }

    GPU_PRIORITY_FILE.write_text(
        json.dumps(
            priority_payload,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    handle = None
    locked = False

    try:
        handle = GPU_LOCK_FILE.open(
            "a+",
            encoding="utf-8",
        )

        deadline = (
            time.monotonic()
            + GPU_LOCK_TIMEOUT_SECONDS
        )

        while True:
            try:
                fcntl.flock(
                    handle.fileno(),
                    fcntl.LOCK_EX
                    | fcntl.LOCK_NB,
                )

                locked = True
                break

            except BlockingIOError:
                if (
                    time.monotonic()
                    >= deadline
                ):
                    raise GPUResourceBusyError(
                        "Shared GTX1060 lock timeout"
                    )

                time.sleep(0.25)

        free_mib = gpu_free_mib()

        if free_mib < GPU_MIN_FREE_MIB:
            raise GPUResourceBusyError(
                "Insufficient free GTX1060 memory"
            )

        print(
            "BONEQC_GPU_GUARD_ACQUIRED "
            f"free_mib={free_mib}",
            flush=True,
        )

        return handle

    except Exception:
        if (
            handle is not None
            and locked
        ):
            try:
                fcntl.flock(
                    handle.fileno(),
                    fcntl.LOCK_UN,
                )
            except OSError:
                pass

        if handle is not None:
            handle.close()

        try:
            GPU_PRIORITY_FILE.unlink(
                missing_ok=True
            )
        except OSError:
            pass

        raise


def release_gpu_guard(
    handle,
) -> None:
    if not GPU_GUARD_ENABLED:
        return

    try:
        if handle is not None:
            try:
                fcntl.flock(
                    handle.fileno(),
                    fcntl.LOCK_UN,
                )
            finally:
                handle.close()

    finally:
        try:
            GPU_PRIORITY_FILE.unlink(
                missing_ok=True
            )
        except OSError:
            pass

        print(
            "BONEQC_GPU_GUARD_RELEASED",
            flush=True,
        )


initialize_gpu_guard()


def load_token() -> str:
    token = TOKEN_FILE.read_text(
        encoding="utf-8",
    ).strip()

    if not token:
        raise RuntimeError(
            "Gateway token is empty"
        )

    return token


def image_exists() -> bool:
    result = subprocess.run(
        [
            "docker",
            "image",
            "inspect",
            IMAGE,
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    )

    return result.returncode == 0


def float_or_none(value):
    if value in (None, ""):
        return None

    return float(value)


def int_or_none(value):
    if value in (None, ""):
        return None

    return int(value)


class Handler(BaseHTTPRequestHandler):
    server_version = "BoneQC-C7-Gateway/0.1.0"

    def log_message(
        self,
        format,
        *args,
    ):
        print(
            "%s - %s"
            % (
                self.address_string(),
                format % args,
            ),
            flush=True,
        )

    def send_json(
        self,
        status: int,
        payload: dict,
    ):
        body = json.dumps(
            payload,
            ensure_ascii=False,
            indent=2,
        ).encode("utf-8")

        self.send_response(status)

        self.send_header(
            "Content-Type",
            "application/json; charset=utf-8",
        )

        self.send_header(
            "Content-Length",
            str(len(body)),
        )

        self.send_header(
            "Cache-Control",
            "no-store",
        )

        self.end_headers()

        self.wfile.write(body)

    def authorized(self) -> bool:
        expected = load_token()

        header = self.headers.get(
            "Authorization",
            "",
        )

        prefix = "Bearer "

        if not header.startswith(prefix):
            return False

        supplied = header[len(prefix):]

        return hmac.compare_digest(
            supplied,
            expected,
        )

    def do_GET(self):
        if self.path == "/health/live":
            self.send_json(
                200,
                {
                    "status": "alive",
                    "service": "boneqc-c7-gateway",
                    "version": "0.1.0",
                },
            )
            return

        if self.path == "/health/ready":
            checks = {
                "token_file": (
                    TOKEN_FILE.is_file()
                    and TOKEN_FILE.stat().st_size > 0
                ),
                "docker_image": image_exists(),
            }

            ready = all(checks.values())

            self.send_json(
                200 if ready else 503,
                {
                    "status": (
                        "ready"
                        if ready
                        else "not_ready"
                    ),
                    "checks": checks,
                },
            )
            return

        self.send_json(
            404,
            {
                "error": "not_found",
            },
        )

    def do_POST(self):
        if self.path != "/v1/analyze":
            self.send_json(
                404,
                {
                    "error": "not_found",
                },
            )
            return

        if not self.authorized():
            self.send_json(
                401,
                {
                    "error": "unauthorized",
                },
            )
            return

        if not JOB_LOCK.acquire(
            blocking=False
        ):
            self.send_json(
                409,
                {
                    "error": "inference_busy",
                },
            )
            return

        try:
            content_length = int(
                self.headers.get(
                    "Content-Length",
                    "0",
                )
            )

            if content_length <= 0:
                self.send_json(
                    400,
                    {
                        "error": "empty_dicom",
                    },
                )
                return

            if content_length > MAX_BODY_BYTES:
                self.send_json(
                    413,
                    {
                        "error": "dicom_too_large",
                        "max_bytes": MAX_BODY_BYTES,
                    },
                )
                return

            dicom = self.rfile.read(
                content_length
            )

            if len(dicom) != content_length:
                self.send_json(
                    400,
                    {
                        "error": "incomplete_body",
                    },
                )
                return

            input_sha256 = hashlib.sha256(
                dicom
            ).hexdigest()

            started = time.perf_counter()

            with tempfile.TemporaryDirectory(
                prefix="boneqc-c7-gateway-"
            ) as tmp:
                root = Path(tmp)

                input_dir = root / "input"
                output_dir = root / "output"

                input_dir.mkdir()
                output_dir.mkdir()

                dicom_path = (
                    input_dir
                    / "input.dcm"
                )

                dicom_path.write_bytes(
                    dicom
                )

                command = [
                    "docker",
                    "run",
                    "--rm",
                    "--gpus",
                    "all",
                    "--network",
                    "none",
                    "--pull",
                    "never",
                    "-v",
                    f"{input_dir}:/input:ro",
                    "-v",
                    f"{output_dir}:/output",
                    IMAGE,
                    "--input",
                    "/input/input.dcm",
                    "--output-dir",
                    "/output",
                ]

                try:
                    gpu_guard = acquire_gpu_guard()

                except GPUResourceBusyError as exc:
                    print(
                        "BONEQC_GPU_GUARD_BUSY "
                        f"{exc}",
                        flush=True,
                    )

                    self.send_json(
                        409,
                        {
                            "error": "gpu_resource_busy",
                        },
                    )

                    return

                try:
                    process = subprocess.run(
                        command,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.STDOUT,
                        text=True,
                        timeout=TIMEOUT_SECONDS,
                        check=False,
                    )

                finally:
                    release_gpu_guard(
                        gpu_guard
                    )

                if process.returncode != 0:
                    self.send_json(
                        500,
                        {
                            "status": "Failure",
                            "stage": "frozen_c7",
                            "exit_code": process.returncode,
                            "log_tail": (
                                process.stdout
                                .splitlines()[-40:]
                            ),
                        },
                    )
                    return

                csv_path = (
                    output_dir
                    / "boneqc-c7-results-v1.csv"
                )

                if not csv_path.is_file():
                    self.send_json(
                        500,
                        {
                            "status": "Failure",
                            "stage": "output",
                            "error": (
                                "result_csv_missing"
                            ),
                        },
                    )
                    return

                with csv_path.open(
                    "r",
                    encoding="utf-8-sig",
                    newline="",
                ) as handle:
                    rows = list(
                        csv.DictReader(handle)
                    )

                if len(rows) != 1:
                    self.send_json(
                        500,
                        {
                            "status": "Failure",
                            "stage": "output",
                            "error": (
                                "expected_exactly_one_row"
                            ),
                            "rows": len(rows),
                        },
                    )
                    return

                row = rows[0]

            elapsed = (
                time.perf_counter()
                - started
            )

            result = {
                "path_to_study": (
                    row.get("path_to_study")
                ),
                "study_uid": (
                    row.get("study_uid")
                ),
                "image_uid": (
                    row.get("image_uid")
                ),
                "anatomical_region": (
                    row.get(
                        "anatomical_region"
                    )
                ),
                "quality_class": int_or_none(
                    row.get("quality_class")
                ),
                "violation_type": (
                    row.get("violation_type")
                    or None
                ),
                "quality_prob": float_or_none(
                    row.get("quality_prob")
                ),
                "processing_status": (
                    row.get(
                        "processing_status"
                    )
                ),
                "time_of_processing": (
                    float_or_none(
                        row.get(
                            "time_of_processing"
                        )
                    )
                ),
            }

            self.send_json(
                200,
                {
                    "status": "Success",
                    "gateway_version": "0.1.0",
                    "runtime_image": IMAGE,
                    "input_sha256": input_sha256,
                    "elapsed_seconds": elapsed,
                    "result": result,
                },
            )

        except subprocess.TimeoutExpired:
            self.send_json(
                504,
                {
                    "status": "Failure",
                    "stage": "frozen_c7",
                    "error": "timeout",
                },
            )

        except Exception as exc:
            self.send_json(
                500,
                {
                    "status": "Failure",
                    "stage": "gateway",
                    "error": type(exc).__name__,
                    "message": str(exc),
                },
            )

        finally:
            JOB_LOCK.release()


def main():
    load_token()

    server = ThreadingHTTPServer(
        (HOST, PORT),
        Handler,
    )

    print(
        f"BONEQC_C7_GATEWAY_LISTEN="
        f"http://{HOST}:{PORT}",
        flush=True,
    )

    print(
        f"BONEQC_C7_IMAGE={IMAGE}",
        flush=True,
    )

    server.serve_forever()


if __name__ == "__main__":
    main()
