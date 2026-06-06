#!/bin/env python
"""PyStack adapter for STAT backend stack sampling."""

import os
import re
import subprocess

_FRAME_RE = re.compile(
    r'^\s+\((?P<kind>Python|C)\)\s+File "(?P<source>.*)",\s+'
    r"line (?P<line>\d+),\s+in (?P<function>.*?)(?:\s+\((?P<object>.*)\))?\s*$"
)
_THREAD_RE = re.compile(
    r"^Traceback for thread (?P<tid>\d+)(?: \((?P<name>[^)]*)\))?.*:\s*$"
)
_FALSE_VALUES = {"0", "false", "no", "off"}


def _enabled(name, default):
    return os.environ.get(name, default).strip().lower() not in _FALSE_VALUES


def _format_frame(line):
    match = _FRAME_RE.match(line)
    if match is None:
        return None

    kind = match.group("kind")
    function = (match.group("function") or "<unknown>").strip()
    source = (match.group("source") or "<unknown>").strip()
    lineno = (match.group("line") or "0").strip()

    if function.endswith(" (inlined)"):
        function = function[: -len(" (inlined)")].rstrip()
    if function == "":
        function = "<unknown>"
    if source == "":
        source = "<unknown>"

    if kind == "C":
        function = "native:%s" % function

    return "%s@%s:%s" % (function, source, lineno)


def _trace_priority(trace, pid):
    tid = trace.get("tid")
    name = (trace.get("name") or "").lower()
    frames = trace.get("frames") or []
    has_python = any(not frame.startswith("native:") for frame in frames)

    if pid is not None and tid == str(pid):
        return 0
    if name in {"python", "python3"}:
        return 1
    if has_python:
        return 2
    return 3


def _parse_pystack_remote(output, pid=None):
    traces = []
    current = None

    def finish_current():
        if current is not None and current["frames"]:
            traces.append(current)

    for line in output.splitlines():
        stripped = line.strip()
        if not stripped:
            continue

        thread_match = _THREAD_RE.match(stripped)
        if thread_match is not None:
            finish_current()
            current = {
                "tid": thread_match.group("tid"),
                "name": thread_match.group("name") or "",
                "index": len(traces),
                "frames": [],
            }
            continue

        frame = _format_frame(line)
        if frame is not None:
            if current is None:
                current = {"tid": "", "name": "", "index": len(traces), "frames": []}
            current["frames"].append(frame)

    finish_current()
    traces.sort(key=lambda trace: (_trace_priority(trace, pid), trace["index"]))

    formatted = []
    for trace in traces:
        formatted.extend(trace["frames"])
        formatted.append("#endtrace")
    return formatted


def _pystack_command(pid):
    pystack = os.environ.get("STAT_PYSTACK", "pystack")
    cmd = [pystack, "--no-color", "remote"]

    if _enabled("STAT_PYSTACK_NO_BLOCK", "0"):
        cmd.append("--no-block")

    if _enabled("STAT_PYSTACK_NATIVE", "1"):
        if _enabled("STAT_PYSTACK_NATIVE_ALL", "0"):
            cmd.append("--native-all")
        else:
            cmd.append("--native")
        if _enabled("STAT_PYSTACK_NATIVE_LAST", "0"):
            cmd.append("--native-last")

    if _enabled("STAT_PYSTACK_LOCALS", "0"):
        cmd.append("--locals")
    if _enabled("STAT_PYSTACK_EXHAUSTIVE", "0"):
        cmd.append("--exhaustive")

    cmd.append(str(pid))
    return cmd


def get_trace(pid):
    """Return STAT-formatted stack traces for a process id.

    STAT_BackEnd expects one frame per line in function@source:line format, with
    #endtrace separating threads. PyStack can inspect SIGSTOP-paused processes,
    so this adapter does not resume the target before collecting a trace.
    """

    proc = subprocess.run(
        _pystack_command(pid),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        universal_newlines=True,
        check=False,
    )
    if proc.returncode != 0:
        detail = (proc.stderr or proc.stdout).strip()
        raise RuntimeError(detail or "pystack remote failed for pid %s" % pid)

    traces = _parse_pystack_remote(proc.stdout, pid)
    if not traces:
        raise RuntimeError("pystack remote produced no parseable frames for pid %s" % pid)

    return "\n".join(traces)
