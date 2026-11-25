"""Phase14 compatibility, labels and population contracts; no outcome selection."""
import hashlib,json
from pathlib import Path
COMMON=('flow_duration','tot_fwd_pkts','tot_bwd_pkts')
DAYS={'Monday':'2017-07-03','Tuesday':'2017-07-04','Wednesday':'2017-07-05','Thursday':'2017-07-06','Friday':'2017-07-07'}
def label(value):
    clean=value.strip() if value is not None else ''
    return None if not clean or clean.casefold()=='label' else int(clean.casefold()!='benign')
def capture(name):
    matches=[day for prefix,day in DAYS.items() if name.casefold().startswith(prefix.casefold())]
    if len(matches)!=1:raise ValueError('Unrecognized external capture filename')
    return matches[0]
def require_mapping(names,configuration,exact=False):
    expected=configuration['source_features'] if exact else configuration['common_features']
    if list(names)!=list(expected):raise ValueError('Feature order differs from frozen contract')
    if exact:raise ValueError('Exact18 archived transfer is unsupported: extraction semantics unverified')
    return True
def verified_receipt(receipt):
    if receipt.get('status')!='validated' or receipt.get('dataset_version')!=1 or len(receipt.get('files',[]))!=8:raise ValueError('External receipt identity differs')
    if receipt['physical_data_rows']!=receipt['eligible_rows']+receipt['excluded_rows']:raise ValueError('External rows do not reconcile')
    if any(len(x['sha256'])!=64 or x['bytes']<=0 for x in receipt['files']):raise ValueError('Missing file content pins')
    return True
