#!/usr/bin/env bash
#SBATCH --job-name=stat-pystack-scope
#SBATCH --nodes=1
#SBATCH --ntasks=4
#SBATCH --cpus-per-task=2
#SBATCH --mem=512M
#SBATCH --time=00:20:00

set -euo pipefail

# Submit from the repository root. The workload uses only Python's standard library.
workload="$SLURM_SUBMIT_DIR/tests/examples/pystack-sampling-scope/rank_scope_demo.py"
exec srun --mpi=none "${STAT_EXAMPLE_PYTHON:-python3}" "$workload" \
    --duration "${STAT_EXAMPLE_DURATION:-1180}"
