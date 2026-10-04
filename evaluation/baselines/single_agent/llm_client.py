"""Isolated Ollama HTTP client. No inference or network activity on import."""
import os
import time
import requests
from evaluation.baselines.common.contracts import decode, number
from evaluation.baselines.single_agent.schema import SCHEMA

MODEL = 'qwen3:1.7b'
OPTIONS = {'num_ctx': 2048, 'num_predict': 512}
TIMEOUT = 35
TELEMETRY = ('total_duration', 'load_duration', 'prompt_eval_count', 'prompt_eval_duration', 'eval_count', 'eval_duration')


class ModelError(Exception):
    def __init__(self, category, telemetry=None):
        super().__init__(category)
        self.category, self.telemetry = category, telemetry or {}


class Client:
    def __init__(self, host=None):
        self.host = (host or os.getenv('OLLAMA_HOST', 'http://localhost:11434')).rstrip('/')

    def generate(self, prompt, system, schema=SCHEMA):
        started = time.monotonic()
        telemetry = {'http_status': None, 'runtime_body': None}
        try:
            response = requests.post(self.host + '/api/generate', json={
                'model': MODEL, 'prompt': prompt, 'system': system, 'stream': False,
                'options': dict(OPTIONS), 'format': schema}, timeout=TIMEOUT)
            telemetry.update(http_status=response.status_code, runtime_body=response.text)
            response.raise_for_status()
            try:
                data = decode(response.text)
            except (ValueError, TypeError):
                raise ModelError('invalid_runtime_response', telemetry)
            if (not isinstance(data, dict) or not isinstance(data.get('response'), str)
                    or data.get('done') is not True or data.get('error')):
                raise ModelError('invalid_runtime_response', telemetry)
            for key in TELEMETRY:
                value = data.get(key)
                telemetry[key] = value if number(value) and value >= 0 else None
            telemetry['done_reason'] = data.get('done_reason')
            count, duration = telemetry['eval_count'], telemetry['eval_duration']
            telemetry['tokens_per_second'] = count / (duration / 1e9) if count is not None and duration and duration > 0 else None
            return {'raw_response': data['response'], 'telemetry': telemetry}
        except requests.Timeout:
            raise ModelError('timeout', telemetry)
        except requests.ConnectionError:
            raise ModelError('connection', telemetry)
        except requests.HTTPError:
            raise ModelError('http', telemetry)
        except requests.RequestException:
            raise ModelError('transport', telemetry)
        finally:
            telemetry['generation_seconds'] = time.monotonic() - started

    def identity(self):
        result = {'model_digest': None, 'ollama_version': None, 'resolved_options': None,
                  'unavailable_reason': 'Effective sampling/thread defaults are not established by this client.'}
        for path, key in [('/api/version', 'version'), ('/api/tags', 'models')]:
            try:
                response = requests.get(self.host + path, timeout=TIMEOUT)
                response.raise_for_status()
                data = decode(response.text)
                if key == 'version': result['ollama_version'] = data.get(key)
                else:
                    for model in data.get('models', []):
                        if model.get('name') == MODEL or model.get('model') == MODEL:
                            result['model_digest'] = model.get('digest')
            except (requests.RequestException, ValueError, TypeError, AttributeError):
                pass
        return result

    def warmup(self):
        # Explicit preload followed by one fixed non-evaluation inference.
        response = requests.post(self.host + '/api/generate', json={'model': MODEL, 'stream': False}, timeout=TIMEOUT)
        response.raise_for_status()
        preload = decode(response.text)
        if not isinstance(preload, dict) or preload.get('done') is not True or preload.get('error'):
            raise ModelError('invalid_runtime_response')
        generated = self.generate('Return the JSON object {"ready":true}.',
            'Return only the requested JSON object.',
            {'type': 'object', 'additionalProperties': False, 'required': ['ready'],
             'properties': {'ready': {'type': 'boolean', 'enum': [True]}}})
        if decode(generated['raw_response']) != {'ready': True}:
            raise ModelError('warmup_invalid', generated['telemetry'])
        return {'preload': preload, 'inference': generated, 'protocol': 'preload-and-fixed-inference-v1'}
