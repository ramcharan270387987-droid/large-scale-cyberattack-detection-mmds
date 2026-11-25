"""Pure scheduling, idempotent triggers and crash-safe immutable version registry."""
import hashlib
import json
import os
from pathlib import Path


def released(arrived, delay, now):
    if delay < 0:
        raise ValueError('Negative label delay')
    return [i for i in arrived if i + delay <= now]


def training_window(initial, available, kind, length):
    ordered = list(dict.fromkeys([*initial, *available]))
    return ordered[-length:] if kind == 'sliding' else ordered


def eligible(trigger, support, minimum, index, last, cooldown, attempts, budget, final=False):
    if final: return False, 'end-of-replay'
    if not trigger: return False, 'no-trigger'
    if attempts >= budget: return False, 'budget'
    if index - last < cooldown: return False, 'cooldown'
    if support < minimum: return False, 'insufficient-new-labels'
    return True, 'eligible'


class Registry:
    def __init__(self, root):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        self.seen = set()
        self.active = self._read_active()

    def _read_active(self):
        p = self.root / 'active.json'
        return json.loads(p.read_text())['model'] if p.exists() else None

    def request(self, identifier):
        if identifier in self.seen: return False
        self.seen.add(identifier)
        return True

    def register(self, identifier, record):
        path = self.root / (identifier + '.json')
        payload = json.dumps(record, sort_keys=True, allow_nan=False, indent=2)
        if path.exists():
            if path.read_text() != payload: raise ValueError('Immutable model version conflict')
        else:
            with path.open('x') as f:
                f.write(payload)
                f.flush()
                os.fsync(f.fileno())

    def activate(self, identifier, fail_before_replace=False):
        if not (self.root / (identifier + '.json')).exists(): raise ValueError('Unknown model')
        temporary = self.root / 'active.pending'
        with temporary.open('w') as f:
            json.dump({'model': identifier}, f)
            f.flush()
            os.fsync(f.fileno())
        if fail_before_replace: raise RuntimeError('Injected interrupted pointer update')
        os.replace(temporary, self.root / 'active.json')
        self.active = identifier


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True).encode()).hexdigest()[:20]
