# layer1/adm/detectors/base_detector.py

from abc import ABC, abstractmethod

class BaseDetector(ABC):
    """
    Common interface for all 5 anomaly detectors.
    Each detector:
      - Consumes from its own detect.* queue
      - Processes the enriched event (feature_vector included)
      - Publishes a result to fusion.results (always – even if no anomaly)
    """

    def __init__(self, input_queue: str, output_exchange: str, routing_key: str):
        self.input_queue = input_queue
        self.output_exchange = output_exchange
        self.routing_key = routing_key

    @abstractmethod
    def detect(self, event: dict) -> dict:
        """
        Core detection logic.
        Args:
            event: enriched event with feature_vector
        Returns:
            dict with keys: event_id, detected (bool), anomaly_type,
                           severity, confidence, model_name, metadata
        """
        pass

    @abstractmethod
    def run(self):
        """Connect to RabbitMQ, consume from input_queue, call detect(),
        publish result to fusion.results."""
        pass