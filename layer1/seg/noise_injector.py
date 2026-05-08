"""
Noise Injector — Temporal Realism and Signal Perturbation

This module adds two types of realism to the generated event stream:

  1. Temporal jitter: inter-arrival times are Poisson-distributed rather than
     uniform, so events arrive in realistic bursts rather than at fixed intervals.
     Normal events and anomaly bursts are interleaved to test false positive rate
     under realistic mixed-signal conditions.

  2. Signal perturbation: a configurable noise level adds small random
     fluctuations to metric_values and context fields. This prevents the anomaly
     detectors from fitting to perfectly clean synthetic signals that would never
     appear in real pipeline data.

All random operations use numpy.random.default_rng(seed) so the output is
fully reproducible given the same seed.
"""
