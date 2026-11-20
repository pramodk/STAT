"""Run one parent and one child per Slurm rank, each with a main and worker thread."""

import argparse
import os
from pathlib import Path
import subprocess
import sys
import threading
import time


def wait_in_workload(deadline):
    while time.monotonic() < deadline:
        time.sleep(0.05)


def rank_worker(deadline):
    wait_in_workload(deadline)


def child_worker(deadline):
    wait_in_workload(deadline)


def rank_main(deadline):
    wait_in_workload(deadline)


def child_main(deadline):
    wait_in_workload(deadline)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--duration", type=int, required=True)
    parser.add_argument("--child", action="store_true")
    args = parser.parse_args()
    rank = os.environ.get("SLURM_PROCID", "0")
    deadline = time.monotonic() + args.duration
    child = None

    if args.child:
        role, main_work, worker_work = "child", child_main, child_worker
    else:
        role, main_work, worker_work = "parent", rank_main, rank_worker
        child = subprocess.Popen([
            sys.executable, str(Path(__file__).resolve()),
            "--duration", str(args.duration), "--child",
        ])

    worker = threading.Thread(target=worker_work, args=(deadline,), name=worker_work.__name__)
    worker.start()
    print(f"READY rank={rank} role={role} pid={os.getpid()} threads={threading.active_count()}", flush=True)
    main_work(deadline)
    worker.join()
    if child is not None and child.wait() != 0:
        raise SystemExit("child process failed")
    print(f"DONE rank={rank} role={role}", flush=True)


if __name__ == "__main__":
    main()
