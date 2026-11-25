"""Exact archived parameter execution; no fitting,networking or user-data cache."""
import json,hashlib,math
from pathlib import Path

def verify(path,expected):
    data=Path(path).read_bytes()
    if hashlib.sha256(data).hexdigest()!=expected:raise ValueError('Model artifact checksum mismatch')
    model=json.loads(data)
    if model.get('schema')!='phase15-portable-v1' or model.get('kind') not in ('LR','RF','KMeans'):raise ValueError('Unsupported model representation')
    names=model['features']
    if len(names)!=18 or len(set(names))!=18 or len(model['medians'])!=18:raise ValueError('Invalid feature contract')
    if not math.isfinite(model['threshold']) or not all(math.isfinite(v) for v in model['medians']):raise ValueError('Invalid model parameters')
    if model['kind']=='LR' and len(model['coefficients'])!=18:raise ValueError('Coefficient schema mismatch')
    if model['kind']=='RF' and (len(model['trees'])!=len(model['tree_weights']) or not model['trees'] or any(w<=0 for w in model['tree_weights'])):raise ValueError('Invalid forest weights')
    if model['kind']=='KMeans' and (not model['centers'] or any(len(c)!=18 for c in model['centers'])):raise ValueError('Invalid centroid map')
    return model

def transformed(model,values):
    if list(values)!=model['features']:raise ValueError('Feature names/order differ from model contract')
    raw=[model['medians'][i] if values[n] is None else (math.copysign(math.log1p(abs(values[n])),values[n]) if model.get('input_transform')=='signed_log1p' else values[n]) for i,n in enumerate(model['features'])]
    if not all(math.isfinite(v) for v in raw):raise ValueError('Nonfinite transformed input')
    scaler=model.get('scaler')
    if scaler:
        raw=[((v-scaler['mean'][i] if scaler['with_mean'] else v)/scaler['std'][i] if scaler['std'][i] else 0.) if scaler['with_std'] else (v-scaler['mean'][i] if scaler['with_mean'] else v) for i,v in enumerate(raw)]
    return raw

def sigmoid(x):
    if x>=0:return 1/(1+math.exp(-x))
    e=math.exp(x);return e/(1+e)

def tree_score(node,x):
    for _ in range(10000):
        if 'probabilities' in node:return node['probabilities'][1]
        node=node['left'] if x[node['feature']]<=node['threshold'] else node['right']
    raise ValueError('Tree traversal budget exceeded')

def predict(model,values):
    x=transformed(model,values);kind=model['kind'];base=dict(model=model['id'],source_version=model['source_version'],imputed_features=[n for n in model['features'] if values[n] is None])
    if kind=='LR':
        contributions=[a*b for a,b in zip(model['coefficients'],x)];logit=model['intercept']+math.fsum(contributions);p=sigmoid(logit)
        return base|dict(label='ATTACK' if p>=model['threshold'] else 'BENIGN',probability=p,threshold=model['threshold'],logit=logit,baseline=model['intercept'],contributions=contributions,output_space='log-odds')
    if kind=='RF':
        p=math.fsum(tree_score(tree,x)*weight for tree,weight in zip(model['trees'],model['tree_weights']))/sum(model['tree_weights'])
        return base|dict(label='ATTACK' if p>=model['threshold'] else 'BENIGN',probability=p,threshold=model['threshold'],output_space='attack probability; uncalibrated model score')
    distances=[math.fsum((a-b)**2 for a,b in zip(x,c)) for c in model['centers']];assigned=min(range(len(distances)),key=lambda i:distances[i]);c=model['centers'][assigned];contributions=[(a-b)**2 for a,b in zip(x,c)];distance=distances[assigned]
    return base|dict(label='NOVEL' if distance>model['threshold'] else 'REFERENCE-LIKE',cluster=assigned,squared_distance=distance,threshold=model['threshold'],contributions=contributions,output_space='squared model-space distance')
