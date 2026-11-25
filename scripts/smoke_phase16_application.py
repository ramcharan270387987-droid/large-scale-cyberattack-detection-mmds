"""Focused existing-app checks without model fitting or expensive research."""
import json,math
from pathlib import Path
from streamlit.testing.v1 import AppTest
from src.interactive import portable,inputs,evidence
ROOT=Path(__file__).resolve().parents[1]
def main():
 app=AppTest.from_file(str(ROOT/'dashboard/advanced_app.py')).run(timeout=45);assert not app.exception and not app.error
 pages=['Executive overview','Interactive inference','Historical replay','Evidence & reproducibility']
 for page in pages:
  app.sidebar.selectbox[0].select(page).run(timeout=45);assert not app.exception and not app.error,page
 records=[]
 for entry in evidence.models():
  m=portable.verify(ROOT/entry['artifact'],entry['sha256']);rows=inputs.parse_csv((ROOT/'dashboard/data/phase15_demo.csv').read_bytes(),m['features']);preds=inputs.batch(m,rows);assert len(preds)==3 and all(x['status']=='valid' for x in preds)
  portable.predict(m,dict.fromkeys(m['features'],None));records.append(entry['id'])
 result=dict(status='PASS',pages=pages,models=records,synthetic_csv_rows_per_model=3,fitting=False,kaggle_jobs=False,prior_full_browser_receipt='reports/phase15_validation/browser.json')
 (ROOT/'reports/phase16_validation/application_smoke.json').write_text(json.dumps(result,indent=2)+'\n');print(result)
if __name__=='__main__':main()
