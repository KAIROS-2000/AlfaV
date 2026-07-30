from __future__ import annotations

import asyncio
import contextlib
import os
import signal
import subprocess
import tempfile
import threading
import time
from dataclasses import dataclass
from typing import Callable, Protocol


@dataclass(frozen=True)
class JudgeTestCase:
    label: str
    input: str
    expected: str


@dataclass(frozen=True)
class JudgeExecutionRequest:
    language: str
    code: str
    tests: list[JudgeTestCase]
    time_limit_ms: int
    memory_limit_mb: int
    max_output_chars: int
    tempdir_prefix: str = "judge-"
    max_parallel_tests: int | None = None
    # The runner assigns a fresh unprivileged UID to each HTTP submission.
    # Generic callers leave this unset and retain their current execution model.
    execution_uid: int | None = None


class JudgeRuntime(Protocol):
    def command_for(self, language: str, script_path: str, memory_limit_mb: int) -> list[str]:
        ...

    def build_env(self) -> dict[str, str]:
        ...

    def preexec_fn(
        self,
        memory_limit_mb: int,
        time_limit_ms: int,
        language: str,
        execution_uid: int | None = None,
    ) -> Callable[[], None] | None:
        ...


_STREAM_READ_CHUNK_BYTES = 16 * 1024
_PROCESS_REAP_TIMEOUT_SECONDS = 1.0
_UTF8_MAX_BYTES_PER_CHAR = 4


class _BoundedOutput:
    """Keep only a small prefix while continuing to drain a subprocess pipe."""

    def __init__(self, max_chars: int):
        # `max_output_chars` is a character limit while pipes carry bytes. Four
        # bytes per character covers UTF-8 without allowing an unbounded buffer.
        self._limit_bytes = max(1, int(max_chars)) * _UTF8_MAX_BYTES_PER_CHAR + 16
        self._data = bytearray()
        self.exceeded = False

    def append(self, chunk: bytes) -> bool:
        remaining = self._limit_bytes - len(self._data)
        if remaining > 0:
            self._data.extend(chunk[:remaining])
        if len(chunk) > max(remaining, 0):
            was_exceeded = self.exceeded
            self.exceeded = True
            return not was_exceeded
        return False

    def text(self, max_chars: int) -> str:
        return truncate_output(
            bytes(self._data).decode("utf-8", errors="replace"), max_chars
        )


def _process_group_kwargs() -> dict:
    # The production runner is Linux-based. Keep the shared engine usable on
    # Windows for local tests, where this Popen option is unsupported.
    return {"start_new_session": True} if os.name == "posix" else {}


def _kill_process_tree(process: subprocess.Popen | asyncio.subprocess.Process) -> None:
    """Kill the dedicated POSIX process group, not just its leader."""

    if os.name == "posix":
        try:
            os.killpg(process.pid, signal.SIGKILL)
            return
        except (ProcessLookupError, PermissionError):
            pass
    with contextlib.suppress(ProcessLookupError):
        process.kill()


def _runtime_preexec_fn(
    runtime: JudgeRuntime,
    memory_limit_mb: int,
    time_limit_ms: int,
    language: str,
    execution_uid: int | None,
) -> Callable[[], None] | None:
    return runtime.preexec_fn(
        memory_limit_mb, time_limit_ms, language, execution_uid
    )


def _runtime_env(runtime: JudgeRuntime, workdir: str) -> dict[str, str]:
    env = dict(runtime.build_env())
    # Keep interpreter scratch files in the worker-owned workspace rather than
    # a shared /tmp location. This also avoids a random numeric UID needing a
    # writable home directory in /etc/passwd.
    env["HOME"] = workdir
    env["TMPDIR"] = workdir
    return env


def _prepare_workspace(
    runtime: JudgeRuntime, workdir: str, execution_uid: int | None
) -> None:
    if execution_uid is None:
        return
    hook = getattr(runtime, "prepare_workspace", None)
    if not callable(hook):
        raise RuntimeError("Runtime does not support isolated execution workspaces.")
    hook(workdir, execution_uid)


def _cleanup_workspace(
    runtime: JudgeRuntime, workdir: str, execution_uid: int | None
) -> None:
    if execution_uid is None:
        return
    hook = getattr(runtime, "cleanup_workspace", None)
    if not callable(hook):
        raise RuntimeError("Runtime does not support isolated execution workspaces.")
    hook(workdir, execution_uid)


def truncate_output(value: str | None, limit: int) -> str:
    text = (value or "").replace("\r\n", "\n").replace("\r", "\n")
    if len(text) <= limit:
        return text
    return f"{text[:limit].rstrip()}\n..."


def normalize_output(value: str | None) -> str:
    normalized = (value or "").replace("\r\n", "\n").replace("\r", "\n")
    lines = [line.rstrip() for line in normalized.split("\n")]
    while lines and lines[-1] == "":
        lines.pop()
    return "\n".join(lines)


def looks_like_compile_error(stderr: str) -> bool:
    lowered = stderr.lower()
    return "syntaxerror" in lowered or "unexpected token" in lowered


def coerce_test_cases(value) -> list[JudgeTestCase]:
    if not isinstance(value, list):
        return []

    rows: list[JudgeTestCase] = []
    for index, item in enumerate(value, start=1):
        if not isinstance(item, dict):
            continue
        label = str(item.get("label") or f"Тест {index}").strip() or f"Тест {index}"
        test_input = str(item.get("input") if item.get("input") is not None else item.get("stdin") or "")
        expected = str(item.get("expected") if item.get("expected") is not None else item.get("stdout") or "")
        if not test_input and not expected:
            continue
        rows.append(JudgeTestCase(label=label, input=test_input, expected=expected))
    return rows


def _limited_result(
    *,
    test: JudgeTestCase,
    stdout: _BoundedOutput,
    duration_ms: int,
    max_output_chars: int,
    error_type: str,
) -> dict:
    messages = {
        "timeout": "Превышен лимит времени.",
        "output_limit": "Превышен лимит вывода.",
    }
    return {
        "label": test.label,
        "input": test.input,
        "expected": test.expected,
        "actual": stdout.text(max_output_chars),
        "stderr": messages[error_type],
        "passed": False,
        "duration_ms": duration_ms,
        "error_type": error_type,
    }


def _drain_sync_pipe(
    pipe, output: _BoundedOutput, output_limit: threading.Event
) -> None:
    try:
        while True:
            chunk = pipe.read(_STREAM_READ_CHUNK_BYTES)
            if not chunk:
                return
            if output.append(chunk):
                output_limit.set()
    finally:
        with contextlib.suppress(OSError):
            pipe.close()


def _write_sync_stdin(pipe, payload: bytes) -> None:
    try:
        pipe.write(payload)
        pipe.flush()
    except (BrokenPipeError, OSError):
        pass
    finally:
        with contextlib.suppress(OSError):
            pipe.close()


def run_test(
    *,
    command: list[str],
    runtime: JudgeRuntime,
    workdir: str,
    test: JudgeTestCase,
    time_limit_ms: int,
    memory_limit_mb: int,
    max_output_chars: int,
    language: str,
    execution_uid: int | None = None,
) -> dict:
    started_at = time.perf_counter()
    process = subprocess.Popen(
        command,
        cwd=workdir,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=_runtime_env(runtime, workdir),
        preexec_fn=_runtime_preexec_fn(
            runtime, memory_limit_mb, time_limit_ms, language, execution_uid
        ),
        close_fds=True,
        **_process_group_kwargs(),
    )
    assert process.stdin is not None
    assert process.stdout is not None
    assert process.stderr is not None

    stdout = _BoundedOutput(max_output_chars)
    stderr = _BoundedOutput(max_output_chars)
    output_limit = threading.Event()
    readers = [
        threading.Thread(
            target=_drain_sync_pipe,
            args=(process.stdout, stdout, output_limit),
            daemon=True,
        ),
        threading.Thread(
            target=_drain_sync_pipe,
            args=(process.stderr, stderr, output_limit),
            daemon=True,
        ),
    ]
    writer = threading.Thread(
        target=_write_sync_stdin,
        args=(process.stdin, test.input.encode("utf-8")),
        daemon=True,
    )
    for thread in readers:
        thread.start()
    writer.start()

    deadline = started_at + time_limit_ms / 1000
    outcome = "completed"
    while process.poll() is None:
        if output_limit.is_set():
            outcome = "output_limit"
            break
        if time.perf_counter() >= deadline:
            outcome = "timeout"
            break
        time.sleep(0.01)

    # This is deliberate even after a successful leader exit: a submitted
    # program must not leave a background child alive for the next test.
    _kill_process_tree(process)
    with contextlib.suppress(subprocess.TimeoutExpired):
        process.wait(timeout=_PROCESS_REAP_TIMEOUT_SECONDS)
    with contextlib.suppress(OSError):
        process.stdin.close()
    for thread in readers:
        thread.join(_PROCESS_REAP_TIMEOUT_SECONDS)
    if any(thread.is_alive() for thread in readers):
        # A detached process should not be able to keep the judge request
        # blocked through inherited pipe descriptors.
        outcome = "timeout" if outcome == "completed" else outcome
        with contextlib.suppress(OSError):
            process.stdout.close()
        with contextlib.suppress(OSError):
            process.stderr.close()
    writer.join(_PROCESS_REAP_TIMEOUT_SECONDS)

    if output_limit.is_set() and outcome == "completed":
        outcome = "output_limit"
    duration_ms = int((time.perf_counter() - started_at) * 1000)
    if outcome != "completed":
        return _limited_result(
            test=test,
            stdout=stdout,
            duration_ms=duration_ms,
            max_output_chars=max_output_chars,
            error_type=outcome,
        )

    return completed_test_result(
        test=test,
        stdout=stdout.text(max_output_chars),
        stderr=stderr.text(max_output_chars),
        returncode=process.returncode or 0,
        duration_ms=duration_ms,
        max_output_chars=max_output_chars,
    )


async def _drain_async_pipe(
    stream: asyncio.StreamReader,
    output: _BoundedOutput,
    output_limit: asyncio.Event,
) -> None:
    while True:
        chunk = await stream.read(_STREAM_READ_CHUNK_BYTES)
        if not chunk:
            return
        if output.append(chunk):
            output_limit.set()


async def _write_async_stdin(
    stream: asyncio.StreamWriter | None, payload: bytes
) -> None:
    if stream is None:
        return
    try:
        stream.write(payload)
        await stream.drain()
    except (BrokenPipeError, ConnectionError, OSError):
        pass
    finally:
        stream.close()
        with contextlib.suppress(BrokenPipeError, ConnectionError, OSError):
            await stream.wait_closed()


async def _finish_async_tasks(tasks: list[asyncio.Task]) -> bool:
    try:
        await asyncio.wait_for(
            asyncio.gather(*tasks, return_exceptions=True),
            timeout=_PROCESS_REAP_TIMEOUT_SECONDS,
        )
        return True
    except asyncio.TimeoutError:
        for task in tasks:
            task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)
        return False


def _close_async_pipe_transports(process: asyncio.subprocess.Process) -> None:
    """Close inherited pipes if a hostile detached child keeps them open."""

    transport = getattr(process, "_transport", None)
    if transport is None:
        return
    for fd in (0, 1, 2):
        with contextlib.suppress(AttributeError, OSError):
            pipe_transport = transport.get_pipe_transport(fd)
            if pipe_transport is not None:
                pipe_transport.close()


async def async_run_test(
    *,
    command: list[str],
    runtime: JudgeRuntime,
    workdir: str,
    test: JudgeTestCase,
    time_limit_ms: int,
    memory_limit_mb: int,
    max_output_chars: int,
    language: str,
    execution_uid: int | None = None,
) -> dict:
    started_at = time.perf_counter()
    kwargs = {
        "cwd": workdir,
        "stdin": asyncio.subprocess.PIPE,
        "stdout": asyncio.subprocess.PIPE,
        "stderr": asyncio.subprocess.PIPE,
        "env": _runtime_env(runtime, workdir),
        "close_fds": True,
    }
    kwargs.update(_process_group_kwargs())
    preexec_fn = _runtime_preexec_fn(
        runtime, memory_limit_mb, time_limit_ms, language, execution_uid
    )
    if preexec_fn is not None:
        kwargs["preexec_fn"] = preexec_fn

    process = await asyncio.create_subprocess_exec(*command, **kwargs)
    assert process.stdout is not None
    assert process.stderr is not None
    stdout = _BoundedOutput(max_output_chars)
    stderr = _BoundedOutput(max_output_chars)
    output_limit = asyncio.Event()
    readers = [
        asyncio.create_task(_drain_async_pipe(process.stdout, stdout, output_limit)),
        asyncio.create_task(_drain_async_pipe(process.stderr, stderr, output_limit)),
    ]
    writer = asyncio.create_task(
        _write_async_stdin(process.stdin, test.input.encode("utf-8"))
    )
    process_wait = asyncio.create_task(process.wait())
    output_wait = asyncio.create_task(output_limit.wait())
    done, _ = await asyncio.wait(
        {process_wait, output_wait}, timeout=time_limit_ms / 1000,
        return_when=asyncio.FIRST_COMPLETED,
    )
    if output_wait in done:
        outcome = "output_limit"
    elif process_wait in done:
        outcome = "completed"
    else:
        outcome = "timeout"

    # Always tear down the group. A successful parent process is not evidence
    # that it did not leave an orphan holding a pipe or consuming resources.
    _kill_process_tree(process)
    if process.stdin is not None:
        process.stdin.close()
    if not process_wait.done():
        try:
            await asyncio.wait_for(
                asyncio.shield(process_wait), timeout=_PROCESS_REAP_TIMEOUT_SECONDS
            )
        except asyncio.TimeoutError:
            process_wait.cancel()
    output_wait.cancel()
    await asyncio.gather(output_wait, return_exceptions=True)

    streams_finished = await _finish_async_tasks([*readers, writer])
    if not streams_finished:
        _close_async_pipe_transports(process)
        if outcome == "completed":
            outcome = "timeout"
    if output_limit.is_set() and outcome == "completed":
        outcome = "output_limit"
    duration_ms = int((time.perf_counter() - started_at) * 1000)
    if outcome != "completed":
        return _limited_result(
            test=test,
            stdout=stdout,
            duration_ms=duration_ms,
            max_output_chars=max_output_chars,
            error_type=outcome,
        )

    return completed_test_result(
        test=test,
        stdout=stdout.text(max_output_chars),
        stderr=stderr.text(max_output_chars),
        returncode=process.returncode or 0,
        duration_ms=duration_ms,
        max_output_chars=max_output_chars,
    )


def completed_test_result(
    *,
    test: JudgeTestCase,
    stdout: str | None,
    stderr: str | None,
    returncode: int,
    duration_ms: int,
    max_output_chars: int,
) -> dict:
    actual = truncate_output(stdout, max_output_chars)
    stderr_text = truncate_output(stderr, max_output_chars)
    if returncode != 0:
        return {
            "label": test.label,
            "input": test.input,
            "expected": test.expected,
            "actual": actual,
            "stderr": stderr_text or f"Процесс завершился с кодом {returncode}.",
            "passed": False,
            "duration_ms": duration_ms,
            "error_type": "compile_error" if looks_like_compile_error(stderr_text) else "runtime_error",
        }

    passed = normalize_output(actual) == normalize_output(test.expected)
    return {
        "label": test.label,
        "input": test.input,
        "expected": test.expected,
        "actual": actual,
        "stderr": stderr_text or None,
        "passed": passed,
        "duration_ms": duration_ms,
        "error_type": None,
    }


def execute_stdio_submission(request: JudgeExecutionRequest, runtime: JudgeRuntime) -> dict:
    if not request.tests:
        raise ValueError("Для запуска нужны тесты.")

    extension = "py" if request.language == "python" else "js"
    with tempfile.TemporaryDirectory(prefix=request.tempdir_prefix) as workdir:
        script_path = os.path.join(workdir, f"main.{extension}")
        with open(script_path, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(request.code)
        _prepare_workspace(runtime, workdir, request.execution_uid)
        try:
            command = runtime.command_for(request.language, script_path, request.memory_limit_mb)
            results = [
                run_test(
                    command=command,
                    runtime=runtime,
                    workdir=workdir,
                    test=test_case,
                    time_limit_ms=request.time_limit_ms,
                    memory_limit_mb=request.memory_limit_mb,
                    max_output_chars=request.max_output_chars,
                    language=request.language,
                    execution_uid=request.execution_uid,
                )
                for test_case in request.tests
            ]
        finally:
            _cleanup_workspace(runtime, workdir, request.execution_uid)

    return build_stdio_report(request, results)


async def async_execute_stdio_submission(request: JudgeExecutionRequest, runtime: JudgeRuntime) -> dict:
    if not request.tests:
        raise ValueError("Для запуска нужны тесты.")

    extension = "py" if request.language == "python" else "js"
    max_parallel_tests = request.max_parallel_tests or len(request.tests)
    max_parallel_tests = max(1, min(max_parallel_tests, len(request.tests)))

    with tempfile.TemporaryDirectory(prefix=request.tempdir_prefix) as workdir:
        script_path = os.path.join(workdir, f"main.{extension}")
        with open(script_path, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(request.code)
        case_workdirs = [
            os.path.join(workdir, f"case-{index}")
            for index, _ in enumerate(request.tests, start=1)
        ]
        for case_workdir in case_workdirs:
            os.mkdir(case_workdir)
        _prepare_workspace(runtime, workdir, request.execution_uid)
        try:
            command = runtime.command_for(request.language, script_path, request.memory_limit_mb)
            semaphore = asyncio.Semaphore(max_parallel_tests)

            async def run_case(index: int, test_case: JudgeTestCase) -> dict:
                case_workdir = case_workdirs[index - 1]
                async with semaphore:
                    return await async_run_test(
                        command=command,
                        runtime=runtime,
                        workdir=case_workdir,
                        test=test_case,
                        time_limit_ms=request.time_limit_ms,
                        memory_limit_mb=request.memory_limit_mb,
                        max_output_chars=request.max_output_chars,
                        language=request.language,
                        execution_uid=request.execution_uid,
                    )

            results = await asyncio.gather(
                *(run_case(index, test_case) for index, test_case in enumerate(request.tests, start=1))
            )
        finally:
            _cleanup_workspace(runtime, workdir, request.execution_uid)

    return build_stdio_report(request, results)


def build_stdio_report(request: JudgeExecutionRequest, results: list[dict]) -> dict:
    passed_count = len([row for row in results if row["passed"]])
    total_count = len(results)
    score = int((passed_count / max(total_count, 1)) * 100)
    first_failed = next((row for row in results if not row["passed"]), None)
    compile_error = first_failed["stderr"] if first_failed and first_failed.get("error_type") == "compile_error" else None
    runtime_error = first_failed["stderr"] if first_failed and first_failed.get("error_type") in {"runtime_error", "timeout", "output_limit"} else None

    if passed_count == total_count:
        feedback = f"Автопроверка пройдена: {passed_count}/{total_count} тестов."
    elif first_failed and first_failed.get("error_type") == "timeout":
        feedback = f"Лимит времени превышен на кейсе «{first_failed['label']}»."
    elif first_failed and first_failed.get("error_type") == "output_limit":
        feedback = f"Лимит вывода превышен на кейсе «{first_failed['label']}»."
    elif first_failed and first_failed.get("error_type") == "compile_error":
        feedback = f"Код не запустился из-за синтаксической ошибки на кейсе «{first_failed['label']}»."
    elif first_failed and first_failed.get("error_type") == "runtime_error":
        feedback = f"Код завершился с ошибкой на кейсе «{first_failed['label']}»."
    else:
        feedback = f"Пройдено {passed_count} из {total_count} тестов. Проверь вывод на первом непройденном кейсе."

    return {
        "mode": "stdin_stdout",
        "runner": "stdin_stdout",
        "language": request.language,
        "passed": passed_count == total_count,
        "score": score,
        "feedback": feedback,
        "tests_passed": passed_count,
        "tests_total": total_count,
        "results": results,
        "compile_error": compile_error,
        "runtime_error": runtime_error,
        "time_limit_ms": request.time_limit_ms,
        "memory_limit_mb": request.memory_limit_mb,
    }
