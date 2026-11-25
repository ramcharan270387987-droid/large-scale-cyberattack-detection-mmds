"""Publication figures from versioned aggregate evidence; no private input records."""
import json,hashlib
from pathlib import Path
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
ROOT=Path(__file__).resolve().parents[1];DEST=ROOT/'reports/figures';DEST.mkdir(exist_ok=True)
plt.rcParams.update({'font.size':10,'axes.spines.top':False,'axes.spines.right':False,'savefig.dpi':180,'svg.fonttype':'none'})
manifest=[]
def read(name):return pd.read_csv(ROOT/'reports'/('phase13_'+name+'.csv'))
def save(fig,name,title,sources,scope):
    fig.suptitle(title,fontsize=13);fig.text(.015,.008,scope,fontsize=8);fig.tight_layout(rect=(0,.04,1,.95))
    for ext in ('png','svg'):
        p=DEST/('phase13_'+name+'.'+ext);fig.savefig(p,bbox_inches='tight');manifest.append({'file':str(p.relative_to(ROOT)),'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'sources':sources,'scope':scope,'title':title})
    plt.close(fig)
def bars(data,value,title,name,sources,scope,feature='feature',limit=12):
    if data.empty:return
    data=data.groupby(feature,dropna=False)[value].mean().sort_values().tail(limit);fig,ax=plt.subplots(figsize=(9,5));ax.barh(data.index.astype(str),data.values,color=['#b25c37' if v<0 else '#266b82' for v in data.values]);ax.set_xlabel(value.replace('_',' '));ax.axvline(0,color='black',linewidth=.6);save(fig,name,title,sources,scope)
def main():
    g=read('global_importance');primary='Primary predictor-group sample ≤1,000 per protocol; descriptive model attribution'
    for method,name,title in [('absolute_scaled_coefficient','lr_coefficients','LR absolute scaled coefficients'),('linear_SHAP_mean_absolute','lr_contributions','LR mean absolute centered contributions (log-odds)'),('native_split_importance','rf_importance','Random forest native feature importance')]:
        data=g[g.method.eq(method)];data=data[data.model.str.contains('random_forest')] if name=='rf_importance' else data
        bars(data,'value',title,name,['reports/phase13_global_importance.csv'],primary)
    bars(g[g.method.eq('native_split_importance')&g.model.str.contains('gradient_boosted')],'value','GBT native feature importance','gbt_importance',['reports/phase13_global_importance.csv'],primary)
    rank=read('rank_agreement');fig,ax=plt.subplots(figsize=(10,6));labels=(rank.model+': '+rank['first']+' / '+rank.second).str.slice(0,95);ax.barh(labels.iloc[::-1],rank.spearman.iloc[::-1]);ax.set_xlabel('Spearman rank correlation (averaged ties)');save(fig,'rank_comparison','Agreement across explanation semantics',['reports/phase13_rank_agreement.csv'],primary)
    # Exact interventional linear SHAP summary, using actual centered attributions.
    data=g[g.method.eq('linear_SHAP_mean_absolute')];p=data.pivot(index='feature',columns='protocol',values='value');fig,ax=plt.subplots(figsize=(8,7));im=ax.imshow(p.values,aspect='auto',cmap='viridis');ax.set_yticks(range(len(p)),p.index);ax.set_xticks(range(len(p.columns)),p.columns);fig.colorbar(im,ax=ax,label='Mean absolute linear SHAP (log-odds)');save(fig,'linear_shap','Validated linear SHAP summary',['reports/phase13_global_importance.csv'],primary+'; interventional training background64')
    local=read('synthetic_local');initial=local[local.policies.str.contains('P0')&local.probe.eq(1)].copy();bars(initial,'contribution','Exact local contribution decomposition: fixed synthetic probe1','local_contributions',['reports/phase13_synthetic_local.csv'],'Archived initial adaptive LR; fixed synthetic input; contributions add to baseline in log-odds',limit=18)
    perm=read('permutation_summary');data=perm[perm.metric.eq('pr_auc')&perm.scope.eq('global')];bars(data,'mean','Permutation importance: mean decrease in PR area','permutation',['reports/phase13_permutation_summary.csv'],primary+'; all3 seeds; averaged across six models')
    shift=read('distribution_shift');bars(shift,'js_bits','Chronological evaluation versus training-bin distributions','distribution_shift',['reports/phase13_distribution_shift.csv'],'Full eligible populations; training-only quantile cuts; JS divergence in bits')
    errors=read('enriched_cases')
    for outcome,name in [('FN','false_negative'),('FP','false_positive')]:bars(errors[errors.outcome.eq(outcome)],'mean_contribution',outcome+' signed LR contribution comparison',name,['reports/phase13_enriched_cases.csv'],'At most8 cases per day/family/outcome; enriched cases; no prevalence interpretation')
    case=read('case_contributions');group=case.groupby(['family','feature']).apply(lambda x:(x.mean_absolute*x.rows).sum()/x.rows.sum(),include_groups=False).reset_index(name='value');top=group.groupby('feature').value.mean().nlargest(8).index;p=group[group.feature.isin(top)].pivot(index='family',columns='feature',values='value');fig,ax=plt.subplots(figsize=(11,5));im=ax.imshow(p.values,aspect='auto',cmap='viridis');ax.set_yticks(range(len(p)),p.index);ax.set_xticks(range(len(p.columns)),p.columns,rotation=70,ha='right');fig.colorbar(im,ax=ax,label='Mean absolute contribution (log-odds)');save(fig,'family_contributions','Family-conditioned centered LR contributions',['reports/phase13_case_contributions.csv'],primary+'; support varies by family')
    novelty=read('novelty');bars(novelty,'mean_squared_contribution','K-Means assigned-centroid distance decomposition','novelty',['reports/phase13_novelty.csv'],'1,000 predictor groups per B/C; squared model-space units; novelty is not attack probability')
    hybrid=read('hybrid');hybrid['path']=hybrid.protocol+': S='+hybrid.supervised_positive.astype(str)+', N='+hybrid.novelty_positive.astype(str)+', H='+hybrid.hybrid_positive.astype(str);bars(hybrid.groupby('path',as_index=False).rows.sum(),'rows','Archived hybrid decision paths','hybrid',['reports/phase13_hybrid.csv'],'Exact reconstructed B OR and C blend rules; matched1,000-group samples',feature='path',limit=16)
    fam=read('family_rejection');fam['path']=fam.protocol+': '+fam.true_family+' → '+fam.predicted_family+' rejected='+fam.rejected.astype(str);bars(fam.groupby('path',as_index=False).rows.sum(),'rows','Family-stage predictions and rejection paths','open_set',['reports/phase13_family_rejection.csv'],'Conditional family-stage sample; A rejection unsupported; binary misses remain separate',feature='path',limit=12)
    adaptive=read('adaptive_coefficients');top=adaptive.groupby('feature').raw_unit_coefficient.apply(lambda x:x.max()-x.min()).nlargest(8).index;p=adaptive[adaptive.feature.isin(top)].pivot(index='feature',columns='policies',values='raw_unit_coefficient');fig,ax=plt.subplots(figsize=(10,5));im=ax.imshow(p.values,aspect='auto',cmap='coolwarm');ax.set_yticks(range(len(p)),p.index);ax.set_xticks(range(len(p.columns)),p.columns);fig.colorbar(im,ax=ax,label='Coefficient / archived training standard deviation');save(fig,'adaptive_coefficients','Adaptive LR coefficient evolution in common raw units',['reports/phase13_adaptive_coefficients.csv'],'Frozen initial versus prespecified activated P1/P2 and P4; no historical decision reassignment')
    stable=read('stability');fig,ax=plt.subplots(figsize=(9,4));
    for i,protocol in enumerate(('A','B')):
        values=stable.loc[stable.protocol.eq(protocol),'spearman'].dropna();ax.scatter([i+j*.006 for j in range(len(values))],values,s=22,label=protocol)
    ax.set_xticks([0,1],['A','B']);ax.set_ylabel('Spearman versus primary explanation');save(fig,'stability','Explanation rank stability',['reports/phase13_stability.csv'],'All sample/background variants, flow weighting and capture deletion; descriptive sensitivity')
    costs=read('cost');bars(costs[costs.stage.isin(['supervised','permutation','components','diagnostics'])],'seconds','Measured whole-stage computational cost','cost',['reports/phase13_cost.csv'],'Private Kaggle single-driver CPU; includes verification and scoring; no deployment-latency claim',feature='stage')
    (ROOT/'manifests/phase13_figures.json').write_text(json.dumps({'figures':manifest,'unique_figures':len(manifest)//2},indent=2)+'\n');print('Generated',len(manifest)//2,'figures in PNG and SVG')
if __name__=='__main__':main()
