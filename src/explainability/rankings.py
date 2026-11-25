"""Rank agreement with averaged ties and explicit method semantics."""
from math import sqrt


def ranks(values):
    ordered=sorted(values,key=lambda name:(values[name],name))
    result={}
    position=0
    while position<len(ordered):
        end=position+1
        while end<len(ordered) and values[ordered[end]]==values[ordered[position]]:
            end+=1
        rank=(position+1+end)/2
        for name in ordered[position:end]:result[name]=rank
        position=end
    return result


def agreement(first, second, top=5):
    common=sorted(set(first)&set(second))
    if len(common)<2:raise ValueError('Insufficient shared features for rank comparison')
    a=ranks({key:first[key] for key in common});b=ranks({key:second[key] for key in common})
    mean_a=sum(a.values())/len(a);mean_b=sum(b.values())/len(b)
    numerator=sum((a[key]-mean_a)*(b[key]-mean_b) for key in common)
    denominator=sqrt(sum((v-mean_a)**2 for v in a.values())*sum((v-mean_b)**2 for v in b.values()))
    first_top=set(sorted(common,key=lambda key:(-first[key],key))[:top])
    second_top=set(sorted(common,key=lambda key:(-second[key],key))[:top])
    return dict(shared_features=len(common),spearman=numerator/denominator if denominator else None,top_k=min(top,len(common)),top_jaccard=len(first_top&second_top)/len(first_top|second_top))
