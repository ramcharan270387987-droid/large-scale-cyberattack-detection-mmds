"""Check supported filter combinations, controls, nulls and empty states."""
import json
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import pandas as pd
from streamlit.testing.v1 import AppTest
from dashboard import phase11_preview as preview

combinations=0
for section in preview.SECTIONS:
    data=preview.load(section)
    columns=[c for c in preview.FILTERS if c in data]
    if not columns:continue
    grouped=data.groupby(columns,dropna=False).size()
    for values,expected in grouped.items():
        values=values if isinstance(values,tuple) else (values,)
        subset=data
        for column,value in zip(columns,values):
            if pd.notna(value):subset=preview.select(subset,column,value)
        # Null is not a selectable filtering value. All-null fields retain their source rows.
        if len(subset)!=expected:
            for column,value in zip(columns,values):
                if pd.isna(value):subset=subset[subset[column].isna()]
        assert len(subset)==expected,(section,values,len(subset),expected)
        combinations+=1

app=AppTest.from_file('dashboard/phase11_preview.py',default_timeout=30).run()
assert not app.exception
sections=list(preview.SECTIONS)+['Detector limitations','Study figures']
for section in sections:
    app.selectbox[0].set_value(section).run()
    assert not app.exception,section
    assert len(app.get('download_button'))==1,section
    keys=[widget.key for widget in app.selectbox if widget.label!='Evidence']
    for key in keys:
        widget=next((w for w in app.selectbox if w.key==key),None)
        if widget is not None and len(widget.options)>1:
            if widget.label=='Figure':
                widget.set_value(sorted((preview.ROOT/'reports/figures').glob('phase11_*.png'))[-1])
            else:
                widget.select_index(len(widget.options)-1)
            app.run()
            assert not app.exception,(section,widget.label)

app.selectbox[0].set_value('Historical alert timeline').run()
next(w for w in app.selectbox if w.label=='Detector').set_value('KSWIN').run()
assert not app.exception and len(app.info)==1
assert app.dataframe[0].value['alert'].isna().all()

empty=AppTest.from_string('''
import pandas as pd
from dashboard import phase11_preview as preview
original=preview.load
try:
    preview.load=lambda section: pd.DataFrame(columns=['detector','value'])
    preview.main()
finally:
    preview.load=original
''',default_timeout=30).run()
assert not empty.exception and len(empty.info)==1 and len(empty.get('download_button'))==0

receipt={'status':'PASS','supported_filter_groups':combinations,'sections':len(sections),'unsupported_KSWIN_alerts':'unavailable','empty_state':'PASS','chart_and_table_controls':'PASS','download_controls':'PASS'}
Path('reports/phase11_validation/preview_final.json').write_text(json.dumps(receipt,indent=2)+'\n')
print(json.dumps(receipt))
