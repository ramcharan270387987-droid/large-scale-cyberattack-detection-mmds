"""Bounded CSV/manual schema checks with aligned outcomes and safe exports."""
import csv,io,math
MAX_BYTES=1024*1024
MAX_ROWS=500
MAX_VALUE=1e12

def parse_values(values,features):
    if list(values)!=list(features):raise ValueError('Required feature names and order differ')
    result={}
    for name in features:
        value=values[name]
        if value is None or str(value).strip()=='':result[name]=None;continue
        try:value=float(value)
        except (ValueError,TypeError):raise ValueError('Nonnumeric feature: '+name) from None
        if not math.isfinite(value) or not 0<=value<=MAX_VALUE:raise ValueError('Feature outside finite [0,1e12] input domain: '+name)
        result[name]=value
    return result

def parse_csv(data,features,max_bytes=MAX_BYTES,max_rows=MAX_ROWS):
    if len(data)>max_bytes:raise ValueError('CSV exceeds1MiB upload limit')
    try:reader=csv.reader(io.StringIO(data.decode('utf-8-sig')),strict=True);header=next(reader)
    except (UnicodeError,csv.Error,StopIteration):raise ValueError('Expected a valid UTF8 CSV with a header') from None
    if len(set(header))!=len(header):raise ValueError('Duplicate CSV columns are not allowed')
    if header!=list(features):
        missing=[n for n in features if n not in header];extra=[n for n in header if n not in features]
        raise ValueError('CSV schema/order mismatch; missing='+','.join(missing)+'; extra='+','.join(extra))
    rows=[]
    try:
        for i,cells in enumerate(reader,1):
            if i>max_rows:raise ValueError('CSV exceeds500row batch limit')
            row=dict(row_number=i,status='valid',error='',values=None)
            try:
                if len(cells)!=len(header):raise ValueError('CSV row has incorrect column count')
                row['values']=parse_values(dict(zip(header,cells)),features)
            except ValueError as exc:row.update(status='invalid',error=str(exc))
            rows.append(row)
    except csv.Error:raise ValueError('Malformed CSV quoting') from None
    if not rows:raise ValueError('CSV contains no data rows')
    return rows

def batch(model,rows):
    from src.interactive.portable import predict
    output=[]
    for row in rows:
        record={k:row[k] for k in ('row_number','status','error')}
        if row['status']=='valid':
            p=predict(model,row['values']);record.update(model=p['model'],label=p['label'],probability=p.get('probability'),squared_distance=p.get('squared_distance'),cluster=p.get('cluster'),threshold=p['threshold'],imputed_count=len(p['imputed_features']))
        output.append(record)
    return output

def safe_csv(rows):
    if not rows:return b''
    keys=list(dict.fromkeys(k for r in rows for k in r));stream=io.StringIO(newline='');writer=csv.DictWriter(stream,keys,lineterminator='\n');writer.writeheader()
    def safe(v):return "'"+v if isinstance(v,str) and (v.lstrip().startswith(('=','+','-','@')) or v.startswith(('\t','\r','\n'))) else v
    writer.writerows({k:safe(v) for k,v in row.items()} for row in rows)
    return stream.getvalue().encode()
