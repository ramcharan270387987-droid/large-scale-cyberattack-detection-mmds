"""Scientific Phase14 figures with explicit populations, configurations and units."""
import json,hashlib
from pathlib import Path
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
ROOT=Path(__file__).resolve().parents[1];DEST=ROOT/'reports/figures';MANIFEST=[]
plt.rcParams.update({'font.size':9,'axes.spines.top':False,'axes.spines.right':False,'svg.fonttype':'none','savefig.dpi':180})
def read(name):return pd.read_csv(ROOT/'reports'/('phase14_'+name+'.csv'))
def save(fig,name,title,sources,topics,note):
    fig.suptitle(title,fontsize=13);fig.text(.01,.005,note,fontsize=8);fig.tight_layout(rect=(0,.045,1,.95));DEST.mkdir(exist_ok=True)
    for ext in ('png','svg'):
        p=DEST/('phase14_'+name+'.'+ext);fig.savefig(p,bbox_inches='tight',metadata={'Date':None} if ext=='svg' else None);MANIFEST.append(dict(file=str(p.relative_to(ROOT)),sha256=hashlib.sha256(p.read_bytes()).hexdigest(),sources=['reports/phase14_'+n+'.csv' for n in sources],topics=topics,note=note,title=title))
    plt.close(fig)
def panelbars(ax,df,x,y,unit):
    df=df.copy();defined=df[y].notna();ax.bar(df.loc[defined,x].astype(str),df.loc[defined,y]);ax.tick_params(axis='x',rotation=65);ax.set_ylabel(unit)
    if not defined.all():ax.text(.02,.95,'Blank/undefined entries omitted',transform=ax.transAxes,va='top',fontsize=8)
def main():
    comp=read('dataset_composition');fig,axes=plt.subplots(1,2,figsize=(12,5));p=comp.pivot(index='dataset',columns='class_name',values='rows');p.plot.bar(ax=axes[0],stacked=True);axes[0].set_ylabel('Observed flows');a=comp[comp.class_name.eq('ATTACK')].copy();a['percent']=a.prevalence*100;panelbars(axes[1],a,'dataset','percent','Attack prevalence (%)');save(fig,'composition','Source and external dataset populations',['dataset_composition'],[1,2],'Exact observed releases; class shares are flow-weighted,not independent repetitions')
    mapping=read('feature_mapping');fig,ax=plt.subplots(figsize=(10,8));supported=mapping.common_transfer_allowed.astype(str).str.lower().eq('true');ax.barh(mapping.source_feature.iloc[::-1],supported.iloc[::-1].astype(int),color=['#267482' if x else '#bbb' for x in supported.iloc[::-1]]);ax.set_xlim(0,1.1);ax.set_xticks([0,1],['Excluded / unverified','Conditional common transfer']);save(fig,'compatibility','Feature compatibility and selected common contract',['feature_mapping'],[3],'Three documented duration/count predictors; exact18-feature archived transfer unsupported; no guessed zeros/conversions')
    dist=read('distribution_support');fig,axes=plt.subplots(1,3,figsize=(15,4.8))
    for ax,feature in zip(axes,dist.feature.unique()):
        data=dist[dist.feature.eq(feature)&dist.condition.eq('all')]
        for _,r in data.iterrows():ax.plot([0,.25,.5,.75,1],json.loads(r['quantiles']),marker='o',label=f"{r['domain']} N={int(r['rows']):,}")
        ax.set_title(feature);ax.set_xlabel('Quantile probability');ax.set_yscale('symlog',linthresh=1);ax.set_ylabel('microseconds' if feature=='flow_duration' else 'packets');ax.legend(fontsize=7)
    save(fig,'distributions','Compatible-feature distributions across collections',['distribution_support'],[4],'Source training population versus all eligible external flows;symlog magnitude axes;extractor/capture differences remain')
    ext=read('external_model_comparison');primary=ext[ext.sensitivity.eq('primary')&ext.operating.eq('validation_budget')];chron=primary[primary.evaluation_protocol.eq('chronological')];learned=chron[chron.model.str.endswith(('-LR','-RF'))].copy();fig,axes=plt.subplots(1,3,figsize=(16,5))
    for ax,metric in zip(axes,['recall','precision','fpr']):
        d=learned.assign(percent=learned[metric]*100);panelbars(ax,d,'model','percent',metric+' (%)')
        if metric=='fpr':ax.axhline(1,ls='--',color='red',label='Validation selection ceiling;not test guarantee');ax.legend(fontsize=7)
    save(fig,'external_models','Frozen source-only versus target-trained common-feature models',['external_model_comparison'],[5,6,7],f'Primary chronological external test N={int(chron.iloc[0].rows):,};3features;source-only andtarget-only validation thresholds')
    curves=read('external_curves');fig,axes=plt.subplots(2,2,figsize=(14,10))
    for i,protocol in enumerate(('chronological','grouped')):
        for model in sorted(curves.model.unique()):
            if not model.endswith(('-LR','-RF')):continue
            d=curves[curves.evaluation_protocol.eq(protocol)&curves.model.eq(model)]
            if d.empty:continue
            axes[i,0].plot(d.fpr,d.recall,label=model);axes[i,1].plot(d.recall,d.precision,label=model)
        for j in (0,1):axes[i,j].set_title(protocol);axes[i,j].legend(fontsize=6);axes[i,j].set_ylim(0,1.02)
        axes[i,0].set_xlabel('Benign FPR (fraction)');axes[i,0].set_ylabel('Attack recall (fraction)');axes[i,1].set_xlabel('Attack recall (fraction)');axes[i,1].set_ylabel('Precision (fraction)');axes[i,1].axhline(primary[primary.evaluation_protocol.eq(protocol)].prevalence.iloc[0],color='gray',ls='--')
    save(fig,'roc_pr','External whole-score ROC and precision–recall curves',['external_curves','external_model_comparison'],[8],'2048-bin tied-score ROC trapezoids/stepPR;horizontalPR line is each matched population attack prevalence')
    fam=read('external_family_metrics');d=fam[fam.evaluation_protocol.eq('chronological')&fam.sensitivity.eq('primary')&fam.operating.eq('validation_budget')&fam.model.str.endswith(('-LR','-RF'))&fam.family.ne('BENIGN')&fam.rows.gt(0)];p=d.pivot(index='family',columns='model',values='recall');fig,ax=plt.subplots(figsize=(12,5));p.plot.bar(ax=ax);ax.set_ylabel('Attack-family recall (fraction)');save(fig,'families','Observed external attack-family detection',['external_family_metrics'],[9],'Chronological retained test only;original external categories;unsupported families absent rather than zero-imputed')
    cal=read('calibration');fig,ax=plt.subplots(figsize=(9,6))
    for model in sorted(learned.model):
        d=cal[cal.model.eq(model)&cal.evaluation_protocol.eq('chronological')].sort_values('mean_probability_bin_midpoint_approx');ax.plot(d.mean_probability_bin_midpoint_approx,d.observed_attack_rate,marker='o',label=model)
    ax.plot([0,1],[0,1],ls='--',color='gray');ax.set_xlabel('Mean predicted probability (2048-bin midpoint approximation)');ax.set_ylabel('Observed attack fraction');ax.legend(fontsize=7);save(fig,'calibration','External reliability without target-test calibration',['calibration'],[10],'Primary chronology;20reliability bins;midpoint approximation error<=1/4096 per score;no refitting on test labels')
    errors=read('failure_analysis');d=errors[errors.model.eq('E2-B-common-LR')&errors.evaluation_protocol.eq('chronological')&errors.sample_kind.eq('enriched_groups')&errors.attribution_visible];fig,axes=plt.subplots(1,2,figsize=(11,4))
    for ax,outcome in zip(axes,('FN','FP')):
        group=d[d.outcome.eq(outcome)];ax.set_title(outcome+' enriched sourceLR cases')
        if group.empty:ax.text(.05,.5,'No supported public attribution stratum',transform=ax.transAxes)
        else:
            n=group.rows.sum();means=sum(np.array(json.loads(r.mean_signed_contributions))*r.rows for r in group.itertuples())/n;ax.bar(['duration','forward packets','backward packets'],means);ax.set_ylabel('Mean signed contribution (log-odds)');ax.tick_params(axis='x',rotation=40)
    save(fig,'failures','Bounded external LR failure explanations',['failure_analysis'],[11],'At most8cases per family/outcome;aggregates<5suppressed;enriched cases do not estimate prevalence;no treeSHAP')
    volume=read('scalability_summary');fig,axes=plt.subplots(1,3,figsize=(16,4.8))
    for work in volume.workload.unique():
        d=volume[volume.workload.eq(work)].sort_values('actual_rows');axes[0].plot(d.actual_rows/1e6,d.median_seconds,marker='o',label=work);axes[1].plot(d.actual_rows/1e6,d.rows_per_second/1e6,marker='o',label=work);axes[2].plot(d.actual_rows/1e6,d.jvm_rss_sampled_peak/1024**2,marker='o',label=work)
    for ax,label in zip(axes,['Median action time (s)','Throughput (million flows/s)','Sampled absolute JVM RSS peak (MiB)']):ax.set_xlabel('Actual observed flows (millions)');ax.set_ylabel(label);ax.legend(fontsize=7)
    save(fig,'volume','Observed data-volume scaling on one CPU machine',['scalability_summary'],[12,13,14],'local[4];16shuffle partitions;snappyParquet;no explicitSpark cache;3measured repetitions;OS cache uncontrolled')
    workers=read('worker_scaling');fig,axes=plt.subplots(1,3,figsize=(15,4.5))
    for work in workers.workload.unique():
        d=workers[workers.workload.eq(work)].sort_values('workers')
        for ax,col in zip(axes,['median_seconds','speedup','efficiency']):ax.plot(d.workers,d[col],marker='o',label=work)
    for ax,label in zip(axes,['Median matched action time (s)','T(1)/T(p) speedup','Speedup / configured workers']):ax.set_xticks([1,2,4]);ax.set_xlabel('Spark local worker threads');ax.set_ylabel(label);ax.legend(fontsize=7)
    save(fig,'workers','Local CPU parallelism and measured efficiency',['worker_scaling'],[15,16,17],'Same approximate1Mpopulation;3repetitions;newSparkContexts in sharedJVM;single machine,not multiple nodes')
    storage=read('storage_comparison');fig,axes=plt.subplots(1,3,figsize=(13,4.6));panelbars(axes[0],storage.assign(MiB=storage.bytes/1024**2),'format','MiB','Stored bytes (MiB)');panelbars(axes[1],storage,'format','read_checksum_seconds','Full numeric read/checksum median (s)');panelbars(axes[2],storage,'format','query_seconds','Projection/filter/group median (s)');save(fig,'storage','CSV and Parquet on identical logical source rows',['storage_comparison'],[18,19],f'N={int(storage.actual_rows.iloc[0]):,};binary IDs losslesslyhex in both;conversion separate;3repetitions;OS cache uncontrolled')
    partition=read('partition_comparison');fig,axes=plt.subplots(1,2,figsize=(11,4.8))
    for ax,matrix in zip(axes,['partition_materialization','partition_query_after_materialization']):
        d=partition[partition.matrix.eq(matrix)];panelbars(ax,d,'configuration','median_seconds',matrix.replace('_',' ')+' (s)');ax.set_xlabel('Requested partitions')
    save(fig,'partitions','Repartition construction and subsequent query cost',['partition_comparison'],[20],'Matched approximate1Mpopulation;4/16/48partitions;AQEdisabled;3repetitions;shuffle/spill bytes not independently retrieved')
    cache=read('cache_comparison');fig,ax=plt.subplots(figsize=(10,5));panelbars(ax,cache,'configuration','median_seconds','Measured action time (s)');save(fig,'cache','Cache materialization versus repeated query cost',['cache_comparison'],[21],'Same rows/query;MEMORY_AND_DISK;first materialization1measurement,warm/uncached3queries;break-even separately tabulated')
    pandas=read('pandas_comparison');fig,axes=plt.subplots(1,3,figsize=(16,4.5))
    for ax,matrix in zip(axes,['Spark_Pandas_input_loading','Spark_Pandas_end_to_end','Spark_Pandas_compute']):
        d=pandas[pandas.matrix.eq(matrix)].copy();d['engine']=d.configuration.str.split('-').str[0]
        for engine in ('spark','pandas'):
            g=d[d.engine.eq(engine)].sort_values('actual_rows');ax.plot(g.actual_rows,g.median_seconds,marker='o',label=engine)
        ax.set_title(matrix.replace('Spark_Pandas_',''));ax.set_xlabel('Matched rows,4columns');ax.set_ylabel('Median action time (s)');ax.legend()
    save(fig,'pandas','Bounded matched Spark and Pandas workloads',['pandas_comparison'],[22],'100k/500k/at most1Mactual rows;3repetitions;loadedSpark data materialized before compute;startup separate;no universal superiority claim')
    cost=read('model_cost');opt=read('optimization_summary');fig,axes=plt.subplots(1,2,figsize=(16,6));fits=cost[cost.model.str.endswith(('-LR','-RF'))].copy();fits['label']=fits.model+' N='+fits.training_rows.astype(str);panelbars(axes[0],fits,'label','fit_seconds','One model fitting action (s)');other=opt[opt.matrix.isin(['archived_inference','pattern_mining'])].copy();other['label']=other.matrix+': '+other.configuration+' N='+other.actual_rows.astype(str);panelbars(axes[1],other,'label','median_seconds','Specified scoring/mining action (s)');save(fig,'cost','Measured model fitting,inference and pattern-mining cost',['model_cost','optimization_summary'],[23],'Common3model fits once each;archived18feature inference3repetitions;FP-Growth100ktransactions,one budgeted fit;timings are batch costs')
    raw=read('scalability_runs');d=raw[raw.workload.eq('analytics')&raw.workers.eq(4)];fig,ax=plt.subplots(figsize=(9,5))
    for req,g in d.groupby('requested_rows'):
        measured=g[~g.warmup];x=measured.actual_rows.iloc[0]/1e6;ax.scatter([x]*len(measured),measured.seconds,label=f'N={int(measured.actual_rows.iloc[0]):,}');ax.plot([x-.08,x+.08],[measured.seconds.median()]*2,color='black');warm=g[g.warmup];ax.scatter([x]*len(warm),warm.seconds,marker='x',color='gray')
    ax.set_xlabel('Actual flows (millions)');ax.set_ylabel('Analytics action time (s)');ax.legend(fontsize=7);save(fig,'variability','Individual repetitions and separate warmups',['scalability_runs'],[24],'Dots=all3measured runs;black segment=median;grayX=warmup;sharedKaggle infrastructure,no significance claim')
    source=read('source_reference');fig,axes=plt.subplots(1,2,figsize=(12,5))
    for ax,metric in zip(axes,['recall','pr_auc']):
        for family in ('LR','RF'):
            src=source[source.model.eq('E2-B-common-'+family)&source.operating.eq('validation_budget')].iloc[0];m=json.loads(src.metrics);external=chron[chron.model.eq('E2-B-common-'+family)].iloc[0];ax.plot(['SourceB-common holdout','External chronological'],[m[metric],external[metric]],marker='o',label=family)
        ax.set_ylabel(metric+' (fraction)');ax.legend()
    save(fig,'source_external_gap','Same frozen common-feature models across collections',['source_reference','external_model_comparison'],[5,6],'Different retained source/external populations and prevalences;descriptive gaps,not causal domain-shift estimates;E0archived18results separate')
    assert set(range(1,25))<=set(t for f in MANIFEST for t in f['topics']);(ROOT/'manifests/phase14_figures.json').write_text(json.dumps(dict(schema='phase14-figures-v1',unique_figures=len(MANIFEST)//2,topic_coverage=sorted(set(t for f in MANIFEST for t in f['topics'])),figures=MANIFEST),indent=2)+'\n');print('FIGURES',len(MANIFEST)//2)
if __name__=='__main__':main()
