"""
Auto-Execution Engine — auto.execute Queue Consumer

This module consumes incidents from the auto.execute RabbitMQ queue and
performs simulated remediation actions for evaluation purposes. In the
evaluation context, remediation is simulated: the three recommended_actions
from the Strategy Agent output are logged with a timestamp, a short sleep
is introduced to simulate realistic execution time, and the outcome is
recorded as SUCCESS (for evaluation, all auto-executions succeed unless a
deliberate failure injection is active for testing purposes).

After each execution, the engine publishes an outcome message to the
outcome.feedback queue with outcome_type = AUTO_EXECUTE_SUCCESS or
AUTO_EXECUTE_FAILURE, the resolution_time_ms, and the full policy result
passed through. This outcome message is consumed by the Layer 2 Learning
Agent to update ChromaDB and recalibrate the EMA threshold.

The executor also writes every action to the SQLite decision log via the
sqlite_logger module with decision_type = AUTO_EXECUTE.
"""
