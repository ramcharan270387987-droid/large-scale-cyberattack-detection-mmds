"""Version-pinned detector adapters with explicit input semantics."""
from math import isfinite,log
from river import drift


def create(name,sensitivity='conservative',seed=23013):
    sensitive=sensitivity=='sensitive'
    if name=='ADWIN':return drift.ADWIN(delta=.01 if sensitive else .001)
    if name=='PageHinkley':return drift.PageHinkley(delta=.005,threshold=10 if sensitive else 30,min_instances=30,mode='both')
    if name=='KSWIN':return drift.KSWIN(alpha=.01 if sensitive else .001,window_size=100,stat_size=30,seed=seed)
    if name=='DDM':return drift.binary.DDM(warm_start=30,warning_threshold=2.,drift_threshold=3.)
    raise ValueError(f'Unknown detector {name}')


def update(detector,value,binary=False):
    if not isfinite(value):return False
    if binary and value not in (0,1):raise ValueError('DDM requires a released binary error')
    detector.update(value)
    return bool(detector.drift_detected)


def divergences(reference,current,smoothing=1e-6):
    if len(reference)!=len(current) or not reference or min(reference+current)<0 or not sum(reference) or not sum(current):
        raise ValueError('Histograms require nonnegative counts and positive support')
    def normalize(values):
        denominator=sum(values)+len(values)*smoothing
        return [(v+smoothing)/denominator for v in values]
    p,q=normalize(reference),normalize(current)
    js=sum(.5*a*log(a/((a+b)/2),2)+.5*b*log(b/((a+b)/2),2) for a,b in zip(p,q))
    psi=sum((b-a)*log(b/a) for a,b in zip(p,q))
    return js,psi
