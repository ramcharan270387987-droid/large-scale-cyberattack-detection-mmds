"""Bounded declared synthetic mechanisms, independent of real attack labels."""
import math,random

SCENARIOS=('stationary','abrupt','gradual','incremental','recurring','variance','correlation','prior','missingness','error','concept')


def generate(kind,seed,size=4096,magnitude=1.):
    if kind not in SCENARIOS:raise ValueError('Unknown synthetic scenario')
    rng=random.Random(seed)
    for i in range(size):
        progress=max(0.,min(1.,(i-2048)/1024))
        changed=i>=2048
        x,y=rng.gauss(0,.5),rng.gauss(0,.5)
        mean=0.
        if kind=='abrupt':mean=magnitude if changed else 0.
        if kind=='gradual':mean=magnitude if rng.random()<progress else 0.
        if kind=='incremental':mean=magnitude*progress
        if kind=='recurring':mean=magnitude if 2048<=i<3072 else 0.
        if kind=='variance' and changed:x*=3*magnitude
        if kind=='correlation' and changed:y=.9*x+.1*y
        missing=kind=='missingness' and rng.random() < (.3 if changed else .01)
        prior=int(rng.random() < (.65 if kind=='prior' and changed else .2))
        truth=int(x>0)
        if kind=='concept' and changed:truth=1-truth
        error=int((int(x>0)!=truth) if kind=='concept' else rng.random() < (.45 if kind=='error' and changed else .05))
        feature=1/(1+math.exp(-(x+mean)))
        signal=(1/(1+math.exp(-x*y*4)) if kind=='correlation' else float(missing) if kind=='missingness' else float(prior) if kind=='prior' else feature)
        yield {'index':i,'signal':signal,'error':error,'missing':missing,'prior':prior}
