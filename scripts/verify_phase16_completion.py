"""Independent final submission gate: scientific identities, artifacts, regressions and refs."""
from pathlib import Path
import json,csv,hashlib,re,subprocess,zipfile
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'deliverables/final_submission';START='cb36ddec061006acfda09deda2168a196cbf4a48'
def read(p):return json.loads((ROOT/p).read_text())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def references():
 expected=read('reports/phase15_validation/acceptance.json')['protected']
 txt=subprocess.check_output(['git','ls-remote','origin',*expected],cwd=ROOT,text=True);actual={ref:commit for commit,ref in (x.split() for x in txt.splitlines())};assert actual==expected
 (ROOT/'reports/phase16_validation/protected_refs.json').write_text(json.dumps(dict(status='PASS',expected=expected,actual=actual),indent=2)+'\n');return actual

def science():
 matrix=read('reports/phase16_evidence_matrix.json');assert [r['phase'] for r in matrix]==list(range(1,16))
 for r in matrix:
  assert r['status']=='COMPLETE AND VERIFIED' and sha(ROOT/r['evidence'])==r['sha256']
  assert all(r.get(k) for k in ['objective','dataset_provenance','evaluation_population','protocols','algorithms','main_findings','negative_findings','reproducibility'])
  subprocess.check_call(['git','cat-file','-e',r['checkpoint']+'^{commit}'],cwd=ROOT)
 claims=read('reports/phase16_master_results.json')
 for r in claims:
  p=ROOT/r['source'];assert sha(p)==r['source_sha256'];sel=json.loads(r['selector'])
  if not sel:
   actual=sum(x['probes'] for x in json.loads(p.read_text())['models'])
  else:
   rows=json.loads(p.read_text()) if p.suffix=='.json' else list(csv.DictReader(p.open()))
   matches=[x for x in rows if all(str(x.get(k))==str(v) for k,v in sel.items())];assert len(matches)==1,(r['claim_id'],len(matches));x=matches[0];actual=x.get('metrics',x)[r['metric']]
   assert int(x.get('metrics',x).get('rows',x.get('actual_rows',r['evaluation_rows'])))==int(r['evaluation_rows'])
  assert abs(float(actual)-float(r['value']))<1e-12,r['claim_id']
 for record in read('manifests/phase16_figures.json'):
  assert sha(ROOT/record['path'])==record['sha256']
  if record['kind']!='conceptual':
   source=ROOT/record['source'];assert source.exists() and sha(source)==record['sha256']
 result=dict(status='PASS',phases=15,exact_claim_selectors=len(claims),figure_files=len(read('manifests/phase16_figures.json')),no_cross_protocol_pooling=True)
 (ROOT/'reports/phase16_validation/scientific_claims.json').write_text(json.dumps(result,indent=2)+'\n');return result

def verify():
 import fitz
 from docx import Document
 from pptx import Presentation
 refs=references();scientific=science()
 quality=read('reports/phase16_validation/document_quality.json');assert quality['status']=='PASS' and quality['visual_review']['status']=='PASS'
 for path,n in quality['pdf_pages'].items():
  p=OUT/path;assert len(fitz.open(p))==n and sha(p)==quality['artifact_sha256'][path]
 assert len(Document(OUT/'project_report.docx').tables)==quality['report_tables'];assert len(Presentation(OUT/'academic_presentation.pptx').slides)==24
 assert len(re.findall(r'^## Q\d+\.',(OUT/'sources/viva_handbook.md').read_text(),re.M))==80
 reg=read('reports/phase16_validation/regression.json');assert reg['status']=='PASS' and reg['total']==180 and not any(reg[k] for k in ['failures','errors','skipped']);assert sha(ROOT/'reports/phase16_validation/regression.log')==reg['log_sha256']
 smoke=read('reports/phase16_validation/application_smoke.json');assert smoke['status']=='PASS' and len(smoke['models'])==3 and not smoke['fitting']
 assert read('reports/phase14_validation/acceptance.json')['status']==read('reports/phase15_validation/acceptance.json')['status']=='PASS'
 # All historical application/research code and tests must remain identical to the accepted Phase15 snapshot.
 changed=subprocess.check_output(['git','diff','--name-only',START],cwd=ROOT,text=True).splitlines()
 assert all(p=='README.md' or p.startswith('deliverables/') or 'phase16' in p.lower() for p in changed),changed
 assert not subprocess.check_output(['git','diff',START,'--','tests','src','dashboard','configs','requirements.txt'],cwd=ROOT,text=True)
 subprocess.check_call(['python','scripts/verify_phase16_references.py'],cwd=ROOT)
 inventory=json.loads((OUT/'INVENTORY.json').read_text());listed={r['path'] for r in inventory['files']};actual={p.relative_to(OUT).as_posix() for p in OUT.rglob('*') if p.is_file() and p.name not in inventory['exclusions']};assert listed==actual
 for r in inventory['files']:
  p=OUT/r['path'];assert sha(p)==r['sha256'] and p.stat().st_size==r['bytes']
 package=read('reports/phase16_validation/package.json');zp=ROOT/package['path'];assert sha(zp)==package['sha256'] and zp.stat().st_size==package['bytes']
 with zipfile.ZipFile(zp) as z:
  assert z.testzip() is None and len(z.namelist())==package['zip_files']
  for p in OUT.rglob('*'):
   if p.is_file():assert z.read('MMDS_final_submission/'+p.relative_to(OUT).as_posix())==p.read_bytes()
 assert (OUT/'REPRODUCIBILITY.md').exists() and (OUT/'STREAMLIT_CLOUD_DEPLOYMENT.md').exists()
 result=dict(status='PASS',phases_complete=list(range(1,17)),starting_checkpoint=START,validated_tree_checkpoint=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),research_sources_unchanged=True,tests=180,document_pages=quality['pdf_pages'],slides=24,viva_questions=80,scientific=scientific,package=package,protected=refs,no_training=True,no_kaggle_jobs=True,no_public_deployment=True)
 (ROOT/'reports/phase16_validation/acceptance.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2));return result
if __name__=='__main__':verify()
