"""Audit actual pinned detector parameters and application contracts."""
from collections import deque
from pathlib import Path
import json
import river
from src.drift.advanced_detectors import create

root=Path(__file__).resolve().parents[1]
frozen=json.loads((root/'reports/phase11_synthetic/frozen.json').read_text())
entries=[]
for name in ('ADWIN','PageHinkley','KSWIN','DDM','JS','PSI'):
    native=name in ('ADWIN','PageHinkley','KSWIN','DDM')
    def parameters(sensitivity):
        return {k:list(v) if isinstance(v,deque) else v for k,v in create(name,sensitivity)._get_params().items()}
    entry={'identifier':name,'algorithm':name,'library':'River '+river.__version__ if native else 'MMDS count-derived divergence',
           'primary_synthetic_configuration':parameters(frozen[name]) if native else {'threshold':frozen[name],'reference_observations':256,'window_observations':64,'bins':10,'smoothing':1e-6,'log_base':2 if name=='JS' else 'e'},
           'historical_configuration':parameters('conservative') if native else {'registry':'reports/phase11_historical/frozen.json'},
           'input_signal':'released binary prediction error' if name=='DDM' else 'bounded observed signal or explicitly declared released aggregate signal' if native else 'reference and current histogram counts',
           'input_granularity':'individual released binary error' if name=='DDM' else 'observations in synthetic tests, explicitly aggregate windows in history' if native else 'fixed histogram window',
           'reference_requirements':'adaptive state, no artificial fixed reference' if native else 'independent calibration-reference bins and counts',
           'primary_reporting_warmup_arrivals':256,
           'evaluation_seeds':[23013,23014,23015],
           'warmup_observations':{'ADWIN':10,'PageHinkley':30,'KSWIN':100,'DDM':30}.get(name,256),
           'label_dependency':'required' if name=='DDM' else 'required only for error or prevalence signals',
           'missing_input_behavior':'unavailable without a detector update; declared skip, independent-reference median or separate missingness sensitivity',
           'minimum_support':'native valid-update warm-up; historical flow support 100, sensitivity 1/100/1000/10000' if native else 'reference and current nonzero counts; historical flow support 100 with explicit sensitivity',
           'reset_semantics':'native library state adaptation by default, separately measured external reconstruction and cooldown' if native else 'fixed reference retained across windows',
           'calibration_provenance':'independent seeds 13013–13015, frozen before evaluation seeds 23013–23015',
           'state_serialization':'trusted internal pickle tested' if native else 'JSON reference bins and counts',
           'validated_populations':['bounded synthetic evaluation','supplemental independent-seed sensitivity'],
           'unsupported_populations':(['historical ordered binary-error monitoring'] if name=='DDM' else ['historical 49-window KSWIN with 100-observation warm-up'] if name=='KSWIN' else []),
           'computational_evidence':['reports/phase11_finalization/costs.csv','reports/phase11_finalization/engineering_costs.csv'] if native else ['reports/phase11_synthetic/synthetic_metrics.csv'],
           'interpretation':'monitoring evidence without attack confirmation or future adaptation efficacy'}
    if name not in ('DDM','KSWIN'):entry['validated_populations'].append('retrospective supported aggregate replay windows')
    entries.append(entry)
registry={'schema':'phase11-detectors-v2','detectors':entries,'controls':{'FixedJS':{'threshold':.1,'source':'reports/phase11_synthetic/synthetic_metrics.csv'},'no_detector':'reports/phase11_robustness/ablations.csv','ensemble':'two distinct label-free families within 64 arrivals, cooldown 64'},'phase12_started':False,'phase12_authorized':False}
(root/'manifests/phase11_detectors.json').write_text(json.dumps(registry,indent=2)+'\n')
print('Audited six detector registry entries')
