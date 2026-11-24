"""Trusted local snapshots with idempotent batch updates."""
import pickle
from src.drift.advanced_detectors import create,update


class DetectorState:
    def __init__(self,name,**parameters):
        self.name=name
        self.parameters=parameters
        self.detector=create(name,**parameters)
        self.batch_ids=set()
        self.observations=0
        self.valid_updates=0
        self.suppressed_updates=0

    def batch(self,identifier,values):
        if identifier in self.batch_ids:return []
        before=self.snapshot()
        alerts=[]
        try:
            for value in values:
                detected=update(self.detector,value,self.name=='DDM')
                if detected is None:
                    if self.suppressed_updates is not None:
                        self.suppressed_updates+=1
                else:
                    if self.valid_updates is not None:
                        self.valid_updates+=1
                    if detected:
                        alerts.append(self.observations)
                self.observations+=1
        except Exception:
            previous=self.restore(before)
            self.__dict__.clear()
            self.__dict__.update(previous.__dict__)
            raise
        self.batch_ids.add(identifier)
        return alerts

    def snapshot(self):return pickle.dumps(self,protocol=5)

    @staticmethod
    def restore(content):
        # Read only trusted experiment snapshots, never uploaded or arbitrary bytes.
        value=pickle.loads(content)
        if not isinstance(value,DetectorState):raise ValueError('Incompatible state snapshot')
        # Legacy snapshots have no valid-update counters. Their history is unknown.
        if not hasattr(value,'valid_updates'):value.valid_updates=None
        if not hasattr(value,'suppressed_updates'):value.suppressed_updates=None
        return value
