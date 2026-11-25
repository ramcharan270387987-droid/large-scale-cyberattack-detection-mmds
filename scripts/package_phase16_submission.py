"""Build a self-contained academic payload inventory and reproducible ZIP listing."""
from pathlib import Path
import json,hashlib,shutil,zipfile
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'deliverables/final_submission';ZIP=ROOT/'deliverables/MMDS_final_submission.zip'
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 validation=OUT/'validation';validation.mkdir(exist_ok=True)
 for name in ['document_quality.json','application_smoke.json','regression.json','references.json','protected_refs.json','scientific_claims.json']:
  shutil.copy(ROOT/'reports/phase16_validation'/name,validation/name)
 for phase in [14,15]:shutil.copy(ROOT/f'reports/phase{phase}_validation/acceptance.json',validation/f'phase{phase}_acceptance.json')
 shutil.copy(ROOT/'manifests/phase16_figures.json',validation/'figure_provenance.json')
 shutil.copy(ROOT/'reports/phase16_evidence_matrix.json',validation/'phase_evidence_matrix.json')
 shutil.copy(ROOT/'reports/phase16_master_results.json',validation/'master_results.json')
 shutil.copy(ROOT/'reports/phase16_completion_report.md',OUT/'COMPLETION_REPORT.md')
 # LaTeX auxiliaries are build caches; the compiled bibliography and source are useful payloads.
 for ext in ['aux','blg','log','out']:
  for p in (OUT/'manuscript').glob('*.'+ext):p.unlink()
 files=sorted(p for p in OUT.rglob('*') if p.is_file() and p.name not in {'INVENTORY.json','SHA256SUMS'})
 rows=[dict(path=p.relative_to(OUT).as_posix(),bytes=p.stat().st_size,sha256=digest(p)) for p in files]
 (OUT/'INVENTORY.json').write_text(json.dumps(dict(schema=1,exclusions=['INVENTORY.json','SHA256SUMS'],files=rows),indent=2)+'\n')
 (OUT/'SHA256SUMS').write_text(''.join(r['sha256']+'  '+r['path']+'\n' for r in rows))
 with zipfile.ZipFile(ZIP,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=7) as z:
  for p in sorted(OUT.rglob('*')):
   if p.is_file():z.write(p,'MMDS_final_submission/'+p.relative_to(OUT).as_posix())
 receipt=dict(path=str(ZIP.relative_to(ROOT)),bytes=ZIP.stat().st_size,sha256=digest(ZIP),payload_files=len(rows),zip_files=len(rows)+2,exclusions='Inventory and checksum exclude themselves; ZIP and final gate receipt are outside payload to avoid circular hashes.')
 (ROOT/'reports/phase16_validation/package.json').write_text(json.dumps(receipt,indent=2)+'\n');(ZIP.with_suffix('.zip.sha256')).write_text(receipt['sha256']+'  '+ZIP.name+'\n');print(receipt)
if __name__=='__main__':main()
