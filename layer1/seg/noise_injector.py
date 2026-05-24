# layer1/seg/noise_injector.py
# Adds Gaussian metric noise to event values for temporal realism.
# Called by SyntheticEventGenerator.generate_corpus() on every event.

import numpy as np


class NoiseInjector:
    """
    Applies ±5% Gaussian noise to all float values in metric_values.
    Skips events where metric_values is not a dict (e.g. type_mutation
    schema drift events where metric_values is deliberately a string).
    """

    def __init__(self, rng: np.random.Generator, noise_pct: float = 0.05):
        self.rng       = rng
        self.noise_pct = noise_pct

    def apply(self, event: dict) -> dict:
        """
        Mutates event['metric_values'] in-place, adding Gaussian noise.
        Returns the event dict (same object).
        """
        mv = event.get("metric_values")

        # Skip if metric_values is not a dict
        # (type_mutation schema drift events have metric_values = string)
        if not isinstance(mv, dict):
            return event

        noisy = {}
        for k, v in mv.items():
            if isinstance(v, (int, float)):
                noise = self.rng.normal(0, abs(float(v)) * self.noise_pct)
                noisy[k] = max(0.0, round(float(v) + noise, 4))
            else:
                noisy[k] = v

        event["metric_values"] = noisy
        return event