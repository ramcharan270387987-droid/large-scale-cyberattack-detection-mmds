"""Full-column numerical audit from the preserved typed external layer."""
from pyspark.sql import functions as F

def all_columns(spark,root,receipt):
    typed=spark.read.option('recursiveFileLookup','true').parquet(str(root/'raw_typed')).where('_parse_ok');header=receipt['files'][0]['header'];expressions=[]
    for i,name in enumerate(header):
        c='c'+str(i)
        if name=='Label':continue
        v=F.expr(f'try_cast({c} as double)');finite=v.isNotNull() & ~F.isnan(v) & (F.abs(v)!=float('inf'))
        expressions.extend([F.sum((F.col(c).isNull() | (F.trim(c)=='')).cast('long')).alias(c+'_missing'),F.sum((v.isNull() & F.col(c).isNotNull() & (F.trim(c)!='')).cast('long')).alias(c+'_malformed_numeric'),F.sum(F.isnan(v).cast('long')).alias(c+'_nan'),F.sum((F.abs(v)==float('inf')).cast('long')).alias(c+'_inf'),F.min(F.when(finite,v)).alias(c+'_min'),F.max(F.when(finite,v)).alias(c+'_max')])
    rows=typed.count();stats=typed.agg(*expressions).first().asDict();return dict(rows=rows,scope='All non-label CSV columns,including unmodeled predictors',features=[dict(index=i,original_name=name,**{k:stats['c'+str(i)+'_'+k] for k in ('missing','malformed_numeric','nan','inf','min','max')}) for i,name in enumerate(header) if name!='Label'])
