# Reproducibility and evidence guide

This package consolidates completed research; it starts no jobs and fits no models. The editable report is project_report.docx, with sources/project_report.md and sources/report_content.json. The separate conference manuscript is manuscript/manuscript.tex, its genuine IEEEtran.cls, references.bib and compiled manuscript.pdf. academic_presentation.pptx contains editable text and speaker notes; sources/presentation_content.json and sources/speaker_notes.md preserve those sources. viva_handbook.docx/PDF and its Markdown include 80 questions, timed scripts, revision card and demo checklist.

## Source checkout and immutable history

Repository: https://github.com/ramcharan270387987-droid/large-scale-cyberattack-detection-mmds

Branch: research-v2. Phase 16 starts from cb36ddec061006acfda09deda2168a196cbf4a48. Each phase checkpoint and its report hash is recorded in tables/phase_completion_matrix.csv and the repository reports/phase16_evidence_matrix.json. tables/master_results.csv records exact source paths, row selectors, values, denominators and SHA256. Archived research reports, manifests, compact model files and scripts are repository dependencies; this ZIP is the academic submission, not a duplicate full research checkout.

Do not pool protocol A, B and C results. Source 16,232,943, strict timestamp 16,232,929, B replay 15,322,987, adaptive primary 1,997,636 and external chronological test 308,939 are separate populations. The external mirror's 2,830,743 eligible rows are not its primary test count. Source-common3 models are newly fitted archived research baselines, not the exact original 18-feature transfer.

## Local application

From a complete repository checkout, use Python 3.12 and the existing dashboard requirements. Dependency installation is a setup instruction, not an action repeated by Phase 16.

```bash
python -m venv .venv-advanced
. .venv-advanced/bin/activate
pip install -r dashboard/requirements.txt
python -m streamlit run dashboard/advanced_app.py --server.address 0.0.0.0 --server.port 8501 --server.headless true --server.maxUploadSize 1 --browser.gatherUsageStats false
```

Open http://localhost:8501. Use synthetic_demo.csv or the repository dashboard/data/phase15_demo.csv. Select supported LR, RF or K-Means. User data must obey the exact 18-feature ordered schema, finite nonnegative values up to 1e12 and the 1-MiB/500-row bounds. Allowed blanks use training medians. Invalid rows remain diagnosed. No Spark, Java, Kaggle token, private model download or training is required by this application. The full repository's approved evidence and compact model registry must be present; the academic ZIP alone is not an application distribution.

## Regenerate academic artifacts

Use an authoring environment with Python 3.12, python-docx, python-pptx, matplotlib, Pillow, PyMuPDF, LibreOffice, pdfLaTeX and BibTeX. These are document-authoring dependencies, separate from the lightweight application. Existing scripts build accepted evidence, conceptual diagrams, report sources and editable documents. Do not rerun research exporters to regenerate documents.

```bash
python scripts/build_phase16_evidence.py
python scripts/build_phase16_diagrams.py
python scripts/build_phase16_report_source.py
python scripts/build_phase16_documents.py
python scripts/build_phase16_presentation.py
python scripts/build_phase16_viva.py
soffice --headless --convert-to pdf --outdir deliverables/final_submission deliverables/final_submission/project_report.docx deliverables/final_submission/academic_presentation.pptx deliverables/final_submission/viva_handbook.docx deliverables/final_submission/speaker_notes.docx
```

Compile the paper from deliverables/final_submission/manuscript:

```bash
pdflatex -interaction=nonstopmode -halt-on-error manuscript.tex
bibtex manuscript
pdflatex -interaction=nonstopmode -halt-on-error manuscript.tex
pdflatex -interaction=nonstopmode -halt-on-error manuscript.tex
```

IEEEtran.cls V1.8b is Michael Shell's licensed conference class. Its original copyright/license header is preserved. The class was obtained from the GitHub mirror https://raw.githubusercontent.com/cslaviero/ieee_paper_markdown_pandoc/master/IEEEtran.cls because direct CTAN access was blocked. The built-in TeX Live ieeetr bibliography style is used. Canonical author metadata, primary-source verification method and date are archived in reports/phase16_validation/references.json; BibTeX uses ASCII transliterations for pdfLaTeX compatibility. The offline reference checker checks that audit's integrity; it does not claim to perform a fresh publisher lookup.

## Scientific checks and private research reproduction

The complete regression suite is `python -m unittest discover -s tests -v` in the established research runtime. It includes Spark checks and requires the archived Spark 4.3.0 override, Python 3.12 and Java 21 configuration documented in the repository Phase 14/15 reports. Installing an arbitrary newer Spark version is not an exact reproduction. The completion validator and document quality checker use the authoring Python environment; the application smoke script requires the dashboard environment.

Private research reruns additionally require authorized pinned data versions, original checksum-verified model artifacts, Kaggle access, the original configuration and the corresponding phase protocols. No credential, authorization header or raw private flow data is included. The final package reproduces document construction and local inference; it does not assert independent recomputation of inaccessible private source experiments.

## Integrity and administrative completion

INVENTORY.json records each payload file's size and SHA256. SHA256SUMS covers the same payload; both exclude themselves to avoid circular hashes. The ZIP is outside this directory, and its checksum is recorded separately. Verify the package before handoff. Replace all `[EDIT ...]` fields, review the institution's formatting rules and rehearse the pacing targets aloud. No signatures, certificates, university approval or manuscript acceptance are asserted.

After the first report PDF export, run `python scripts/paginate_phase16_report.py` and export project_report.docx again. This inserts actual rendered page numbers into contents, figure and table lists. Run `python scripts/check_phase16_documents.py` after all exports and manuscript compilation have finished; do not run it concurrently with a PDF writer. It verifies page counts, text bounds, slide notes, citation resolution and Office structures and creates actual page-render contact sheets. Visual review remains a separate recorded check.
