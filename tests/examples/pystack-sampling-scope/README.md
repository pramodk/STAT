# PyStack sampling scope

Use this workload to compare thread and child-process sampling in STAT GUI. Slurm starts four ranks. Each rank runs a Python
parent and one child, with a main thread and one worker thread in each process.

From the repository root, submit the job with any partition or account options required by your site.

```sh
sbatch tests/examples/pystack-sampling-scope/job.sbatch
```

The job has a 20-minute time limit. The workload waits for about 19 minutes and 40 seconds by default. To shorten it, set
`STAT_EXAMPLE_DURATION` in seconds before submitting. Set `STAT_EXAMPLE_PYTHON` to use a specific Python executable.

Wait for eight `READY` lines with `threads=2` in the Slurm output. In STAT GUI, search for the Slurm job ID and attach
with PyStack to the main `srun`. If two `srun` rows have the same command line, choose the parent of the other `srun`.
The GUI host must be reachable by LaunchMON from the compute node, and the node must allow debugger attachment.

| With Children | With Threads | Expected Python frames on ranks `[0-3]` |
|---|---|---|
| Off | Off | `rank_main` |
| Off | On | `rank_main`, `rank_worker` |
| On | Off | `rank_main`, `child_main` |
| On | On | `rank_main`, `rank_worker`, `child_main`, `child_worker` |

Enable **Clear on Sample** when comparing scopes. With both options enabled, **Sample Multiple** also lets you inspect
the merged 3D graph. Detach when finished so the workload can complete.
