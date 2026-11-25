"""Streamlit integration and graceful-failure checks over the actual app."""
import json
from pathlib import Path
from streamlit.testing.v1 import AppTest
from unittest.mock import patch
from src.interactive import evidence
ROOT=Path(__file__).resolve().parents[1]
def main():
    app=AppTest.from_file(str(ROOT/'dashboard/advanced_app.py')).run(timeout=45);assert not app.exception
    pages=['Executive overview',*evidence.catalog()['groups'],'Interactive inference','Historical replay','Evidence & reproducibility'];checks=[]
    for page in pages:
        app.sidebar.selectbox[0].select(page).run(timeout=45);assert not app.exception,page;assert not app.error,(page,[x.value for x in app.error]);checks.append(page)
    app.sidebar.selectbox[0].select('Interactive inference').run(timeout=30)
    for entry in evidence.models():
        next(s for s in app.selectbox if s.label=='Executable model').select(entry).run(timeout=30)
        next(b for b in app.button if b.label=='Run inference').click().run(timeout=30);assert not app.exception and not app.error;assert any(m.label=='Predicted class' for m in app.metric)
    with patch('src.interactive.portable.verify',side_effect=ValueError('checksum')):
        app.run(timeout=30);assert not app.exception and any('disabled' in x.value for x in app.error)
    # Empty and undefined tables are legitimate evidence states.
    import pandas as pd
    empty=AppTest.from_string("from dashboard import advanced_app as p\np.table=lambda entry:p.pd.DataFrame()\np.main()\n").run();empty.sidebar.selectbox[0].select('Supervised & hybrid').run();assert not empty.exception and any('No supported evidence' in x.value for x in empty.info)
    undefined=AppTest.from_string("from dashboard import advanced_app as p\np.table=lambda entry:p.pd.DataFrame({'recall':[float('nan')]})\np.main()\n").run();undefined.sidebar.selectbox[0].select('Clustering & novelty').run();assert not undefined.exception and any('undefined' in x.value for x in undefined.caption)
    r=dict(status='PASS',modules=checks,models_executed=3,model_unavailable=True,empty_state=True,undefined_metric=True);p=ROOT/'reports/phase15_validation/preview.json';p.write_text(json.dumps(r,indent=2)+'\n');print(r)
if __name__=='__main__':main()
