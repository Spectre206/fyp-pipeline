# Source in every Node 2 application pane before starting the selected controller.
# Supply RABBITMQ_USER and RABBITMQ_PASS securely at runtime; no credentials here.
# The application helper fixes the vhost to fyp.
export RABBITMQ_HOST=10.10.10.11
export RABBITMQ_PORT=5672
export OLLAMA_HOST=http://localhost:11434
