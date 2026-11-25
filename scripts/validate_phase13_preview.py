"""AppTest checks for actual evidence, filters, empty and undefined states."""
import importlib.util,json
from pathlib import Path
import pandas as pd
from streamlit.testing.v1 import AppTest
ROOT=Path(__file__).resolve().parents[1]
def main():
    spec=importlib.util.spec_from_file_location('phase13_preview',ROOT/'dashboard/phase13_preview.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
    app=AppTest.from_file(str(ROOT/'dashboard/phase13_preview.py')).run(timeout=30);assert not app.exception
    count=0
    for section in m.SECTIONS:
        app.selectbox[0].select(section).run(timeout=30);assert not app.exception;assert len(app.dataframe)==1;count+=1
    frame=pd.DataFrame({'protocol':['A'],'mean':[None]});assert m.select(frame,'protocol','B').empty
    empty=AppTest.from_string("import streamlit as st\nfrom dashboard import phase13_preview as p\np.load=lambda section: p.pd.DataFrame()\np.main()\n").run(timeout=30);assert not empty.exception and any('No supported observations' in x.value for x in empty.info)
    undefined=AppTest.from_string("import streamlit as st\nfrom dashboard import phase13_preview as p\np.load=lambda section: p.pd.DataFrame({'protocol':['A'],'feature':['x'],'value':[float('nan')]})\np.main()\n").run(timeout=30);assert not undefined.exception and any('undefined' in x.value for x in undefined.caption)
    out=ROOT/'reports/phase13_validation';out.mkdir(exist_ok=True);receipt=dict(status='PASS',sections=count,empty_state=True,undefined_metric=True,unsupported_filter_empty=True,exceptions=0);(out/'preview.json').write_text(json.dumps(receipt,indent=2)+'\n');print(receipt)
if __name__=='__main__':main()
