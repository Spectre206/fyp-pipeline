"""
Cohen's Kappa Calculator — Risk Tier Agreement

This script calculates Cohen's Kappa between the Strategy Agent's risk_tier
output and the ground truth risk_tier from labels.csv. Kappa measures the
agreement between the two raters beyond what would be expected by chance,
making it more informative than raw accuracy for imbalanced label distributions.

The script reads the per-event CSV from calculate_metrics.py (which contains
both the predicted and ground truth risk_tier for every event), computes the
confusion matrix, and reports: raw accuracy, Cohen's Kappa, and the per-class
precision and recall for LOW and HIGH risk tiers.

The Phase 2 target is Kappa ≥ 0.6 with RAG context enabled. This script is
also used for the RAG hypothesis test (H1) in Phase 2 to compare Kappa before
and after ChromaDB context injection.
"""
