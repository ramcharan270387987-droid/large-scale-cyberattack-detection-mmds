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

    def batch(self,identifier,values):
        if identifier in self.batch_ids:return []
        alerts=[]
        for value in values:
            if update(self.detector,value,self.name=='DDM'):alerts.append(self.observations)
            self.observations+=1
        self.batch_ids.add(identifier)
        return alerts

    def snapshot(self):return pickle.dumps(self,protocol=5)

    @staticmethod
    def restore(content):
        # Read only trusted experiment snapshots, never uploaded or arbitrary bytes.
        value=pickle.loads(content)
        if not isinstance(value,DetectorState):raise ValueError('Incompatible state snapshot')
        return value
