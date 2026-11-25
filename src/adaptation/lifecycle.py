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
        pointer=self.root / 'active.json'
        self.active_threshold=json.loads(pointer.read_text()).get('threshold_bin') if pointer.exists() else None

    def _read_active(self):
        p = self.root / 'active.json'
        return json.loads(p.read_text())['model'] if p.exists() else None

    def request(self, identifier):
        requests=self.root / 'requests'
        requests.mkdir(exist_ok=True)
        marker=requests / (digest(identifier)+'.json')
        try:
            with marker.open('x') as stream:
                json.dump({'request':identifier},stream)
                stream.flush()
                os.fsync(stream.fileno())
        except FileExistsError:
            return False
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

    def activate(self, identifier, fail_before_replace=False, *, threshold=None):
        if not (self.root / (identifier + '.json')).exists(): raise ValueError('Unknown model')
        if threshold is not None and (not isinstance(threshold,int) or not 0<=threshold<=2048):raise ValueError('Invalid operating threshold')
        temporary = self.root / 'active.pending'
        with temporary.open('w') as f:
            json.dump({'model': identifier,'threshold_bin':threshold}, f)
            f.flush()
            os.fsync(f.fileno())
        if fail_before_replace: raise RuntimeError('Injected interrupted pointer update')
        os.replace(temporary, self.root / 'active.json')
        self.active = identifier
        self.active_threshold=threshold


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True).encode()).hexdigest()[:20]


def role_support(rows):
    """Normalize Spark partition types at the model-support boundary."""
    return {(r['source_day'],int(r['split_rank'])):int(r['count']) for r in rows}


def validate_coverage(original,retained,flagged,expected_flagged):
    if retained!=original or flagged!=expected_flagged:
        raise ValueError('Capture-only population coverage differs from verified source')
