---
title: Kinetic Monte Carlo, but in parallel
date: 2026-05-14
---
KMC is stubbornly sequential: each event depends on the state left behind by the previous one. You can't parallelise *within* a trajectory without changing the physics. But you almost never need one trajectory — you need thousands, for statistics, for different conditions, for every node a tree search wants to expand.

So the pattern I've settled on is embarrassingly parallel and embarrassingly effective: one big SLURM allocation, one Python process, and a `multiprocessing.Pool` fanning trajectories across every core in the job.

```python
with multiprocessing.Pool(processes=n_cores) as pool:
    results = pool.map(run_trajectory, conditions)
```

A few things I learned the slow way:

- Seed every worker explicitly. Forked processes that share a random state produce beautifully identical "independent" trajectories.
- Return small summaries from workers, not full lattice histories — pickling a million-site lattice through a pipe is where wall time goes to die.
- One 64-core job beats 64 single-core jobs. The scheduler queue is part of your runtime whether you like it or not.

None of this is clever. That's the point — the cleverness budget belongs to the physics, and the parallelism should be too boring to think about.
