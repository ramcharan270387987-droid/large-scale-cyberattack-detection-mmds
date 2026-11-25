"""AppTest evidence sections plus explicit empty and undefined states."""
import json
from pathlib import Path
from streamlit.testing.v1 import AppTest
ROOT=Path(__file__).resolve().parents[1]
def main():
    from dashboard import phase14_preview as preview
    app=AppTest.from_file(str(ROOT/'dashboard/phase14_preview.py')).run(timeout=45);assert not app.exception
    for section in preview.SECTIONS:
        app.selectbox[0].select(section).run(timeout=45);assert not app.exception,section;assert len(app.dataframe)>=1,section
    empty=AppTest.from_string("from dashboard import phase14_preview as p\np.load=lambda section:p.pd.DataFrame()\np.main()\n").run(timeout=30);assert not empty.exception and len(empty.info)==1
    undefined=AppTest.from_string("from dashboard import phase14_preview as p\np.load=lambda section:p.pd.DataFrame({'dataset':['x'],'recall':[float('nan')]})\np.main()\n").run(timeout=30);assert not undefined.exception and any('undefined' in v.value for v in undefined.caption)
    out=ROOT/'reports/phase14_validation/preview.json';out.write_text(json.dumps(dict(status='PASS',sections=len(preview.SECTIONS),empty_state=True,undefined_metric=True,exceptions=0),indent=2)+'\n');print(out.read_text())
if __name__=='__main__':main()
