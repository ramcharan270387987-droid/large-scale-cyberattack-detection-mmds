"""Known mechanisms, separately reported from historical Spark experiments."""
import hashlib
import json
import pickle
import time
from pathlib import Path
import numpy as np
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline
from src.adaptation.lifecycle import digest
from src.adaptation.evaluation import BINS

MECHANISMS=('stationary','feature-shift','prior-shift','abrupt-conditional','gradual-conditional','recurring')


def generate(mechanism,seed,windows=48,rows=512):
    if mechanism not in MECHANISMS: raise ValueError('Unknown mechanism')
    rng=np.random.default_rng(seed); result={}
    for w in range(windows):
        x=rng.normal(size=(rows,18))
        if mechanism=='prior-shift':
            y=(rng.random(rows)<(.2 if w<22 else .7)).astype(int)
            x[:,0]=rng.normal(2*y-1,1)
        else:
            if mechanism=='feature-shift' and w>=22: x[:,0]+=2
            coefficient=2.
            if mechanism in ('abrupt-conditional','recurring') and w>=22: coefficient=-2.
            if mechanism=='recurring' and w>=36: coefficient=2.
            if mechanism=='gradual-conditional': coefficient=2-4*np.clip((w-22)/13,0,1)
            p=1/(1+np.exp(-coefficient*x[:,0]))
            y=(rng.random(rows)<p).astype(int)
        # Role is a deterministic function of predictors, independent of label and day.
        hashes=np.array([int.from_bytes(hashlib.sha256(b'23013'+row.tobytes()).digest()[:8],'big')%10000 for row in x])
        role=np.where(hashes<7000,0,np.where(hashes<8500,1,2))
        result[w]=(x,y,role)
    return result


class SyntheticBackend:
    kind='synthetic'; family='LR'; min_class=10
    def __init__(self,mechanism,seed,root):
        self.name=f'{mechanism}-seed{seed}'
        self.seed=seed; self.mechanism=mechanism; self.root=Path(root)/self.name
        self.root.mkdir(parents=True,exist_ok=True)
        self.data=generate(mechanism,seed); self.initial=list(range(4)); self.calibration=[4,5]; self.forward=list(range(6,48))
        self.meta={}; self.models={}; self.cache={}; self.scores={}; self.physical_fits=0
        values=np.concatenate([self.data[d][0][self.data[d][2]==0,0] for d in self.initial])
        self.edges=np.unique(np.quantile(values,np.linspace(0,1,11))[1:-1])
        self.reference=np.histogram(values,bins=np.r_[-np.inf,self.edges,np.inf])[0].tolist()
    def clock(self,day): return day*60.
    def rows(self,days,role):
        if not days: return np.empty((0,18)),np.empty(0,dtype=int)
        return (np.concatenate([self.data[d][0][self.data[d][2]==role] for d in days]),
                np.concatenate([self.data[d][1][self.data[d][2]==role] for d in days]))
    def support(self,days,role): return len(self.rows(days,role)[1])
    def eval_support(self,day): return len(self.data[day][1])
    def distribution(self,day): return np.histogram(self.data[day][0][:,0],bins=np.r_[-np.inf,self.edges,np.inf])[0].tolist()
    def fit(self,days):
        key=digest([self.name,self.family,days])
        if key in self.models: return key
        x,y=self.rows(days,0)
        if min(np.bincount(y,minlength=2))<self.min_class: raise ValueError('Insufficient training class support')
        start=time.monotonic()
        model=make_pipeline(SimpleImputer(strategy='median'),StandardScaler(),LogisticRegression(C=20,max_iter=200,random_state=self.seed))
        model.fit(x,y); trained=time.monotonic()-start
        probes=np.vstack([np.zeros(18),np.arange(18),np.full(18,np.nan)])
        before=model.predict_proba(probes)
        target=self.root/(key+'.pkl'); t=time.monotonic(); target.write_bytes(pickle.dumps(model)); saved=time.monotonic()-t
        t=time.monotonic(); loaded=pickle.loads(target.read_bytes()); after=loaded.predict_proba(probes); reloaded=time.monotonic()-t
        if not np.array_equal(before,after) or not np.isfinite(after).all(): raise ValueError('Reload mismatch')
        self.models[key]=loaded; self.physical_fits+=1
        self.meta[key]={'model':key,'family':self.family,'backend':self.name,'training_days':days,
                        'rows':len(y),'classes':np.bincount(y,minlength=2).tolist(),'features':18,
                        'fit_seconds':time.monotonic()-start,'training_seconds':trained,
                        'serialization_seconds':saved,'reload_seconds':reloaded,'bytes':target.stat().st_size,
                        'sha256':hashlib.sha256(target.read_bytes()).hexdigest(),'archive':str(target),
                        'reload_probe':after.tolist(),'independent_reload':True,'preprocessing_fit_role':0}
        return key
    def verify(self,key):
        if self.meta[key]['features']!=18: raise ValueError('Feature schema mismatch')
        p=Path(self.meta[key]['archive'])
        if hashlib.sha256(p.read_bytes()).hexdigest()!=self.meta[key]['sha256']: raise ValueError('Hash mismatch')
        loaded=pickle.loads(p.read_bytes()); probes=np.vstack([np.zeros(18),np.arange(18),np.full(18,np.nan)])
        if loaded.predict_proba(probes).tolist()!=self.meta[key]['reload_probe']: raise ValueError('Probe mismatch')
        self.models[key]=loaded
    def score(self,key,day,role):
        cache=(key,day,role)
        if cache not in self.scores:
            x,y=self.rows([day],role); scores=self.models[key].predict_proba(x)[:,1]
            if not np.isfinite(scores).all(): raise ValueError('Nonfinite scores')
            bins=np.minimum((scores*BINS).astype(int),BINS-1)
            hist={}
            for b,label in zip(bins,y): hist.setdefault(int(b),[0,0])[label]+=1
            # Preserve issued raw scores once per unique model, window and role in private local artifacts.
            np.savez_compressed(self.root/f'{key}-{day}-r{role}.npz',score=scores,label=y)
            self.scores[cache]={'synthetic':hist}
        return self.scores[cache]
    def hist(self,key,days,role):
        from src.adaptation.evaluation import merge
        return merge([h for d in days for h in self.score(key,d,role).values()])


def run_all(output):
    from src.adaptation.prequential_runner import run
    output=Path(output); output.mkdir(parents=True,exist_ok=True)
    result=[]; metadata=[]; start=time.monotonic()
    for mechanism in MECHANISMS:
        for seed in (23013,23014,23015):
            backend=SyntheticBackend(mechanism,seed,output/'private-models')
            for delay in (0,1,3):
                for policy in ('P0','P1','P2','P3','P6'):
                    result.append(run(backend,policy,delay,output/'registries'/f'{backend.name}-{policy}-{delay}',
                                      budget=6,period=8,sliding=8,minimum=50))
            if seed==23013:
                for opts in ({'advanced':True},{'cooldown':0},{'minimum':100}):
                    result.append(run(backend,'P2',0,output/'registries'/f'{backend.name}-{digest(opts)}',
                                      **({'budget':6,'period':8,'sliding':8,'minimum':50}|opts)))
            metadata.extend(backend.meta.values())
            (output/'synthetic_results.json').write_text(json.dumps({'runs':result,'models':metadata,'elapsed_seconds':time.monotonic()-start},allow_nan=False))
            print('SYNTHETIC_COMPLETE',mechanism,seed,len(result),flush=True)
    return result

if __name__=='__main__':
    import sys
    run_all(sys.argv[1])
