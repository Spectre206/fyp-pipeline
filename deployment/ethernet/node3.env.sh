# Source in every Django, HITL consumer and Auto Executor pane before startup.
# Supply RABBITMQ_USER and RABBITMQ_PASS securely at runtime; no credentials here.
# The application helper fixes the vhost to fyp.
export RABBITMQ_HOST=10.10.10.11
export RABBITMQ_PORT=5672
