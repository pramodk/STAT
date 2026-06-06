#!/bin/env python
"""py-spy adapter for STAT backend stack sampling."""

import os
import re
import subprocess

_FRAME_RE = re.compile(r"^\s*(?P<function>.*?)\s+\((?P<source>.*):(?P<line>\d+)\)\s*$")
_FALSE_VALUES = {"0", "false", "no", "off"}


def _format_frame(line):
    match = _FRAME_RE.match(line)
    if match:
        function = match.group("function").strip() or "<unknown>"
        source = match.group("source").strip() or "<unknown>"
        lineno = match.group("line").strip() or "0"
        return "%s@%s:%s" % (function, source, lineno)

    frame = line.strip()
    if not frame or frame.startswith("Process ") or frame.startswith("Python v"):
        return None
    return "%s@<unknown>:0" % frame


def _parse_pyspy_dump(output):
    traces = []
    current = []
    for line in output.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith("Thread "):
            if current:
                traces.extend(current)
                traces.append("#endtrace")
                current = []
            continue
        frame = _format_frame(line)
        if frame is not None:
            current.append(frame)

    if current:
        traces.extend(current)
        traces.append("#endtrace")

    return traces


def _format_native_frame(line):
    stripped = line.strip()
    if not stripped.startswith("#"):
        return None

    source = "<native>"
    lineno = "0"
    frame = re.sub(r"^#\d+\s+", "", stripped)
    at_match = re.search(r"\s+at (?P<source>.*):(?P<line>\d+)$", frame)
    from_match = re.search(r"\s+from (?P<source>\S+)$", frame)

    if at_match:
        source = at_match.group("source").strip() or source
        lineno = at_match.group("line").strip() or lineno
        frame = frame[: at_match.start()].rstrip()
    elif from_match:
        source = from_match.group("source").strip() or source
        frame = frame[: from_match.start()].rstrip()

    if " in " in frame:
        frame = frame.split(" in ", 1)[1]
    if " (" in frame:
        frame = frame.split(" (", 1)[0]
    function = frame.strip() or "<native>"
    return "native:%s@%s:%s" % (function, source, lineno)


def _native_trace_enabled():
    return os.environ.get("STAT_PYSPY_NATIVE", "1").strip().lower() not in _FALSE_VALUES


def _native_trace_strict():
    return os.environ.get("STAT_PYSPY_NATIVE_STRICT", "0").strip().lower() not in _FALSE_VALUES


def _get_native_traces(pid):
    if not _native_trace_enabled():
        return []

    gdb = os.environ.get("STAT_PYSPY_NATIVE_CMD", "gdb")
    proc = subprocess.run(
        [
            gdb,
            "-nx",
            "-batch",
            "-q",
            "-p",
            str(pid),
            "-ex",
            "set pagination off",
            "-ex",
            "thread apply all bt",
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        universal_newlines=True,
        check=False,
    )
    if proc.returncode != 0:
        if _native_trace_strict():
            raise RuntimeError(proc.stderr.strip() or "gdb native stack failed for pid %s" % pid)
        message = (proc.stderr or proc.stdout).strip().splitlines()
        detail = message[0] if message else "gdb native stack failed for pid %s" % pid
        return ["native_stack_unavailable@%s:0" % detail, "#endtrace"]

    traces = []
    current = []
    for line in proc.stdout.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith("Thread "):
            if current:
                traces.extend(current)
                traces.append("#endtrace")
                current = []
            continue
        frame = _format_native_frame(line)
        if frame is not None:
            current.append(frame)

    if current:
        traces.extend(current)
        traces.append("#endtrace")

    return traces


def get_trace(pid):
    """Return STAT-formatted Python and native stack traces for a process id.

    STAT_BackEnd expects one frame per line in function@source:line format, with
    #endtrace separating threads. py-spy dump output is intentionally parsed
    conservatively so unknown frame formats still produce a usable node.
    """

    pyspy = os.environ.get("STAT_PYSPY", "py-spy")
    proc = subprocess.run(
        [pyspy, "dump", "--pid", str(pid)],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        universal_newlines=True,
        check=False,
    )
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr.strip() or "py-spy dump failed for pid %s" % pid)

    traces = _parse_pyspy_dump(proc.stdout)
    traces.extend(_get_native_traces(pid))

    return "\n".join(traces)
