"""Exercise evidence sections, real widgets, supported groups and empty states."""
import json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import pandas as pd
from streamlit.testing.v1 import AppTest
from dashboard import phase12_preview as preview

def main():
    app=AppTest.from_file('dashboard/phase12_preview.py',default_timeout=45).run();assert not app.exception
    combinations=0;sections=list(preview.SECTIONS)+['Research limitations','Study figures']
    for section in sections:
        app.selectbox[0].set_value(section).run();assert not app.exception,section
        if section in preview.SECTIONS:
            data=preview.load(section)
            if not data.empty:assert len(app.get('download_button'))==1,section
            columns=[c for c in preview.FILTERS if c in data]
            if columns:
                for values,count in data.groupby(columns,dropna=False).size().items():
                    values=values if isinstance(values,tuple) else (values,);subset=data
                    for column,value in zip(columns,values):
                        subset=subset[subset[column].isna()] if pd.isna(value) else preview.select(subset,column,value)
                    assert len(subset)==count;combinations+=1
        keys=[w.key for w in app.selectbox if w.label!='Evidence']
        for key in keys:
            widget=next((w for w in app.selectbox if w.key==key),None)
            if widget is not None and len(widget.options)>1:
                if widget.label=='Figure':widget.set_value(sorted((preview.ROOT/'reports/figures').glob('phase12_*.png'))[-1])
                else:widget.select_index(len(widget.options)-1)
                app.run();assert not app.exception,(section,key)
    app.selectbox[0].set_value('Synthetic benchmark').run()
    next(w for w in app.selectbox if w.key=='Synthetic benchmarkpolicy').set_value('P2').run()
    next(w for w in app.selectbox if w.key=='Synthetic benchmarkadvanced').set_value(True).run()
    assert not app.exception and app.dataframe[0].value['advanced'].eq(True).all()
    app.selectbox[0].set_value('Attack-family performance').run()
    next(w for w in app.selectbox if w.key=='Attack-family performancefamily').set_value('Benign').run()
    assert not app.exception and app.dataframe[0].value['recall'].isna().all() and len(app.info)==1
    empty=AppTest.from_string('''
import pandas as pd
from dashboard import phase12_preview as preview
original=preview.load
try:
    preview.load=lambda section:pd.DataFrame()
    preview.main()
finally:
    preview.load=original
''').run()
    assert not empty.exception and len(empty.info)==1 and len(empty.get('download_button'))==0
    receipt={'status':'PASS','sections':len(sections),'supported_filter_groups':combinations,'all_widget_selections':'PASS','empty_state':'PASS'}
    dest=preview.ROOT/'reports/phase12_validation';dest.mkdir(exist_ok=True);(dest/'preview.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(receipt))
if __name__=='__main__':main()
