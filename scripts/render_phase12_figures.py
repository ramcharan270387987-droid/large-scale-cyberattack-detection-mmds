"""Measured historical/synthetic/fault panels, no fabricated empirical marks."""
from pathlib import Path
import json
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
ROOT=Path(__file__).resolve().parents[1];R=ROOT/'reports';F=R/'figures';F.mkdir(exist_ok=True)
plt.rcParams.update({'font.size':9,'axes.spines.top':False,'axes.spines.right':False})

def save(fig,name):
    fig.tight_layout();fig.savefig(F/('phase12_'+name+'.png'),dpi=140,bbox_inches='tight');plt.close(fig)
def read(name):
    p=R/('phase12_'+name+'.csv');return pd.read_csv(p) if p.exists() else pd.DataFrame()
def primary(data):
    if data.empty:return data
    for col,value in [('backend','E-LR-seed23013-sample125-weight1'),('budget',3),('sliding',2),('cooldown',2),('minimum',200)]:
        if col in data:data=data[data[col].eq(value)]
    return data

def main():
    # Architecture and information timeline are explanatory, not empirical results.
    fig,axes=plt.subplots(2,1,figsize=(11,5))
    boxes=['Verified feature roles','Active saved model','Issue predictions','Release eligible labels','Fit candidate / validate','Future activation']
    for ax in axes:ax.axis('off')
    for i,label in enumerate(boxes):
        x=.02+(i%3)*.33;y=.72-(i//3)*.55
        axes[0].text(x,y,label,transform=axes[0].transAxes,bbox={'boxstyle':'round,pad=.5','fc':'#e8f1f5'},fontsize=9)
    axes[0].set_title('Adaptive architecture · schematic · fixed evaluation groups never enter fitting')
    axes[1].text(.02,.65,'Arrival → active-version scoring → label-free monitoring → eligible label release → candidate decision',transform=axes[1].transAxes)
    axes[1].text(.02,.2,'Completion = logical arrival + measured action duration; activation waits for a later arrival',transform=axes[1].transAxes)
    axes[1].set_title('Predict-before-update timeline · schematic')
    save(fig,'architecture_and_clocks')
    policies=primary(read('policy_comparison'));p0=policies[policies.delay.eq(0)] if not policies.empty else policies
    if not p0.empty:
        fig,axes=plt.subplots(2,2,figsize=(10,7))
        for ax,metric in zip(axes.flat,['recall','precision','fpr','pr_auc']):
            ax.bar(p0.policy,p0[metric]*100);ax.set(title='Historical E · '+metric.replace('_',' '),ylabel='Percent')
            if metric=='fpr':ax.axhline(1,color='red',ls='--',label='Validation budget, not evaluation bound');ax.legend(fontsize=7)
        save(fig,'historical_policy_metrics')
    windows=read('prequential_metrics');events=read('training_events');triggers=read('trigger_events')
    if not windows.empty:
        runs=set(p0.run);w=windows[windows.run.isin(runs)]
        fig,axes=plt.subplots(3,1,figsize=(11,9))
        versions={v:i for i,v in enumerate(w.model.unique())}
        for policy,group in w.groupby('policy'):
            axes[0].plot(group.window,group.recall*100,'o-',label=policy)
            axes[1].plot(group.window,group.model.map(versions),'o-',label=policy)
        released=windows[windows.run.str.startswith('E-LR-seed23013-sample125-weight1-') & windows.policy.eq('P0')]
        for delay,group in released.groupby('delay'):
            axes[2].plot(group.window,group.label_release_index,'o-',label='delay '+str(delay))
        for ax in axes:ax.legend(ncol=7,fontsize=7);ax.set_xlabel('Historical capture index')
        axes[0].set_ylabel('Forward recall (%)');axes[1].set_ylabel('Saved model categorical index');axes[2].set_ylabel('Label release arrival index')
        axes[0].set_title('Historical E · recall, active versions and label clocks')
        save(fig,'historical_versions_and_labels')
    if not triggers.empty:
        fig,axes=plt.subplots(2,1,figsize=(10,6))
        data=triggers[triggers.run.isin(set(p0.run))]
        shared=data.groupby('window',as_index=False).js.first()
        axes[0].plot(shared.window,shared.js,'o-',label='Shared model-independent input JS')
        for policy,group in data.groupby('policy'):
            selected=group[group.eligible.eq(True)];axes[1].scatter(selected.window,[policy]*len(selected),label=policy)
        axes[0].axhline(.1,color='red',ls='--',label='Frozen JS .1');axes[0].set(ylabel='JS divergence (bits)',title='Historical E · fixed input reference and eligible requests');axes[0].legend(ncol=4,fontsize=7)
        axes[1].set(xlabel='Historical capture index',ylabel='Eligible refresh policy')
        save(fig,'drift_and_requests')
    if not events.empty:
        fits=events[events.action.eq('fit')].copy()
        fig,axes=plt.subplots(1,2,figsize=(11,4))
        fits.groupby(['policy','accepted'],dropna=False).size().unstack(fill_value=0).plot.bar(ax=axes[0],rot=0)
        axes[0].set(title='Historical candidate decisions · all declared sensitivities',ylabel='Actions')
        fits.groupby('policy').charged_fit_seconds.sum().plot.bar(ax=axes[1],rot=0)
        axes[1].set(title='Charged counterfactual fitting',ylabel='Measured fit seconds charged per request')
        save(fig,'candidate_decisions_and_cost')
    thresholds=read('threshold_history')
    if not thresholds.empty:
        fig,ax=plt.subplots(figsize=(10,4))
        for run,group in thresholds.groupby('run'):
            ax.plot(group.window,group.new_bin.where(group.new_bin<2048,2049)/2048,'o-',label='delay '+str(group.delay.iloc[0]))
        ax.set(xlabel='Historical capture index',ylabel='Probability-bin threshold',title='Historical E · validation-only threshold history');ax.legend(fontsize=7)
        save(fig,'thresholds')
    if not policies.empty:
        fig,axes=plt.subplots(1,2,figsize=(11,4))
        for policy,group in policies.groupby('policy'):
            axes[0].plot(group.delay,group.recall*100,'o-',label=policy)
            axes[1].plot(group.charged_fit_seconds,group.recall*100,'o',label=policy)
        axes[0].set(xlabel='Simulated label delay (capture arrivals)',ylabel='Recall (%)',title='Historical label-delay sensitivity')
        axes[1].set(xlabel='Charged adaptation fit wall time (seconds)',ylabel='Recall (%)',title='Historical E · cost and detection');axes[0].legend(ncol=4,fontsize=7)
        save(fig,'label_delays_and_cost_benefit')
    families=read('family_metrics')
    if not families.empty:
        subset=families[families.run.isin(set(p0.run)) & ~families.family.eq('Benign')]
        fig,ax=plt.subplots(figsize=(11,5));subset.pivot_table(index='family',columns='policy',values='recall',aggfunc='first').mul(100).plot.bar(ax=ax,rot=25)
        ax.set(ylabel='Attack-family recall (%)',title='Historical E · family/day confounding remains');save(fig,'attack_families')
    retention=read('retention')
    if not retention.empty:
        fig,axes=plt.subplots(1,2,figsize=(10,4));axes[0].scatter(retention.incumbent_recall*100,retention.candidate_recall*100,c=retention.accepted.map({True:1,False:0}));axes[1].scatter(retention.incumbent_fpr*100,retention.candidate_fpr*100)
        for ax,metric in zip(axes,['recall','FPR']):
            limit=100 if metric=='recall' else max(1,1.1*max(retention.incumbent_fpr.max(),retention.candidate_fpr.max())*100)
            ax.set(xlabel='Incumbent retention '+metric+' (%)',ylabel='Candidate retention '+metric+' (%)');ax.plot([0,limit],[0,limit],ls='--',alpha=.3)
        fig.suptitle('Fixed historical retention diagnostics · separate from forward generalization');save(fig,'retention')
    synthetic=read('synthetic_metrics');sw=pd.read_csv(R/'phase12_synthetic/windows.csv')
    fig,axes=plt.subplots(3,2,figsize=(12,11))
    mechanisms=['stationary','feature-shift','prior-shift','abrupt-conditional','gradual-conditional','recurring']
    for ax,mechanism in zip(axes.flat,mechanisms):
        subset=sw[sw.run.str.startswith(mechanism+'-seed23013-') & sw.delay.eq(0)]
        for policy,group in subset.groupby('policy'):
            # Default runs only, identified by primary period/cooldown/support tags.
            group=group[group.run.str.endswith('-c2-m50-aFalse')]
            ax.plot(group.day,group.recall.rolling(3,min_periods=1).mean()*100,label=policy,alpha=.8)
        ax.axvline(22,color='black',ls='--');ax.set(title='Synthetic · '+mechanism,xlabel='Synthetic window',ylabel='3-window mean recall (%) · descriptive')
    axes[0,0].legend(ncol=5,fontsize=7);save(fig,'synthetic_mechanisms')
    robustness=read('robustness')
    if not robustness.empty:
        fig,ax=plt.subplots(figsize=(11,5));labels=robustness.policy+' d'+robustness.delay.astype(str)+' '+robustness.backend.str.replace('E-','')
        ax.scatter(range(len(robustness)),robustness.recall*100);ax.set_xticks(range(len(labels)));ax.set_xticklabels(labels,rotation=90,fontsize=6);ax.set(ylabel='Recall (%)',title='Historical bounded policy/window/model/sample sensitivities');save(fig,'ablations')
    perf=read('performance')
    if not perf.empty:
        physical=perf[perf.scope.eq('physical-fit')];fig,ax=plt.subplots(figsize=(10,4))
        for metric in ('preprocessing_seconds','training_seconds','save_reload_seconds'):
            if metric in physical:ax.plot(range(len(physical)),physical[metric],'o-',label=metric.replace('_',' '))
        ax.set(xlabel='Unique physical fit index',ylabel='Measured wall seconds',title='Historical Spark CPU · physical fitting overhead');ax.legend(fontsize=7);save(fig,'computational_overhead')
    faults=read('faults')
    if not faults.empty:
        fig,ax=plt.subplots(figsize=(10,5));ax.barh(faults.fault,faults['pass'].astype(int));ax.set(xlabel='Verified injected-fault outcome (1 = pass)',title='Controlled failure and actual rollback tests · no natural-event claim',xlim=(0,1.2));save(fig,'fault_recovery')
    print('Rendered',len(list(F.glob('phase12_*.png'))),'Phase12 figures')
if __name__=='__main__':main()
