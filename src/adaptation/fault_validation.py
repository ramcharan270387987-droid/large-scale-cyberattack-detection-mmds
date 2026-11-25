"""Controlled failures, kept separate from natural historical rollback events."""
import hashlib
import json
import time
from pathlib import Path
from unittest.mock import patch
import numpy as np
from src.adaptation.synthetic_benchmark import SyntheticBackend
from src.adaptation.lifecycle import Registry
from src.adaptation.prequential_runner import run


def validate(root):
    root=Path(root);root.mkdir(parents=True,exist_ok=True);rows=[]
    def record(name,operation,expected=(ValueError,RuntimeError,OSError,EOFError)):
        t=time.monotonic()
        try:operation()
        except expected as exc:rows.append({'fault':name,'observed':type(exc).__name__,'pass':True,'seconds':time.monotonic()-t})
        else:raise AssertionError('Expected failure missing: '+name)
    b=SyntheticBackend('stationary',23013,root/'models');a=b.fit(b.initial);c=b.fit(list(range(6,14)))
    initial=b.meta[a]['reload_probe'];target=Path(b.meta[c]['archive']);original=target.read_bytes();original_hash=b.meta[c]['sha256']
    target.write_bytes(b'corrupted');record('invalid_serialization',lambda:b.verify(c))
    b.meta[c]['sha256']=hashlib.sha256(target.read_bytes()).hexdigest()
    record('failed_independent_reload',lambda:b.verify(c),expected=(Exception,))
    target.write_bytes(original);b.meta[c]['sha256']=original_hash;b.verify(c)
    b.meta[c]['features']=17;record('incompatible_feature_schema',lambda:b.verify(c));b.meta[c]['features']=18
    r=Registry(root/'registry');r.register(a,b.meta[a]);r.register(c,b.meta[c]);r.activate(a);r.activate(c)
    record('interrupted_registry_promotion',lambda:r.activate(a,True))
    assert Registry(root/'registry').active==c
    t=time.monotonic();b.verify(a);r.activate(a)
    assert Registry(root/'registry').active==a and b.meta[a]['reload_probe']==initial
    rows.append({'fault':'actual_saved_model_rollback','observed':'restored original scoring probes','pass':True,'seconds':time.monotonic()-t})
    assert r.request('same-batch') and not Registry(root/'registry').request('same-batch')
    rows.append({'fault':'duplicate_request_after_recovery','observed':'suppressed persistent request','pass':True})
    r.register('compatible',{'features':18});r.activate('compatible')
    assert Registry(root/'registry').active=='compatible'
    rows.append({'fault':'recovery_after_interrupted_promotion','observed':'single committed active pointer','pass':True})
    bad=SyntheticBackend('stationary',23014,root/'bad-train')
    x,y,role=bad.data[0];bad.data[0]=(x,np.zeros_like(y),role)
    record('insufficient_training_class_support',lambda:bad.fit([0]))
    with patch('pathlib.Path.write_bytes',side_effect=OSError('injected storage failure')):
        record('failed_serialization_write',lambda:bad.fit([1,2]))
    # Actual runner failure path must preserve all forward predictions under its incumbent.
    for name in ('failed_candidate_training','missing_validation_labels','invalid_prediction_scores'):
        backend=SyntheticBackend('stationary',23015,root/name)
        original_fit=backend.fit;calls=[0]
        def injected_fit(days):
            calls[0]+=1
            if calls[0]>1:
                if name=='failed_candidate_training':raise RuntimeError('injected fitting failure')
                key=original_fit(days)
                if name=='invalid_prediction_scores':
                    class Invalid:
                        def predict_proba(self,x):return np.full((len(x),2),np.nan)
                    backend.models[key]=Invalid()
                return key
            return original_fit(days)
        backend.fit=injected_fit
        if name=='missing_validation_labels':
            for day in backend.forward:
                x,y,role=backend.data[day];y=y.copy();y[role==1]=0;backend.data[day]=(x,y,role)
        result=run(backend,'P1',0,root/(name+'-registry'),budget=2,period=8,sliding=8,minimum=50)
        assert result['summary']['promotions']==0 and result['summary']['failed_actions']==2
        assert len({w['model'] for w in result['windows']})==1
        rows.append({'fault':name,'observed':'two rejected actions, incumbent served every window','pass':True})
    (root/'fault_receipt.json').write_text(json.dumps(rows,indent=2)+'\n')
    return rows

if __name__=='__main__':
    import sys
    print(json.dumps(validate(sys.argv[1]),indent=2))
