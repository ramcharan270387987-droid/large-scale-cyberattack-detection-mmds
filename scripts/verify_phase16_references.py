"""Check the archived primary-source bibliography audit; no new network claim."""
import json,re
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def main():
 refs=json.loads((ROOT/'reports/phase16_validation/references.json').read_text())
 bib=(ROOT/'deliverables/final_submission/manuscript/references.bib').read_text()
 assert len(refs)==12 and len({r['key'] for r in refs})==12
 for r in refs:
  assert all(r.get(k) for k in ('title','authors','venue','year','url','verification_method','verified_on'))
  assert r['status']=='verified' and r['url'].startswith('https://')
  assert '{'+r['key']+',' in bib
  if r.get('doi'):assert re.match(r'10\.\d{4,9}/\S+',r['doi'])
 print('PASS: 12 bibliographic records match the archived primary-source inspection; offline integrity check only.')
if __name__=='__main__':main()
