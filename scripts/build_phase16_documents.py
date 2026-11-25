"""Render editable academic artifacts from archived Phase 16 sources."""
import json,re,csv,unicodedata
from pathlib import Path
from docx import Document
from docx.shared import Inches,Pt,Cm,RGBColor
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'deliverables/final_submission'
DATA=json.loads((OUT/'sources/report_content.json').read_text())
def plain(s):
 s=re.sub(r'\[([^\]]+)\]\([^)]+\)',r'\1',s)
 return s.replace('**','').replace('`','').replace('\\_','_')
def base():
 d=Document();sec=d.sections[0];sec.page_height=Cm(29.7);sec.page_width=Cm(21);sec.top_margin=Cm(2);sec.bottom_margin=Cm(2);sec.left_margin=Cm(2.3);sec.right_margin=Cm(2.3)
 style=d.styles['Normal'];style.font.name='Times New Roman';style.font.size=Pt(11);style.paragraph_format.space_after=Pt(5);style.paragraph_format.line_spacing=1.08
 for name in ['Heading 1','Heading 2','Heading 3']:
  d.styles[name].font.name='Calibri';d.styles[name].font.color.rgb=RGBColor.from_string('17365D')
  d.styles[name].paragraph_format.keep_with_next=True
 h=sec.header.paragraphs[0];h.text='MMDS | Leakage-aware cyberattack detection';h.style='Caption'
 f=sec.footer.paragraphs[0];f.alignment=2;r=f.add_run();fld=OxmlElement('w:fldSimple');fld.set(qn('w:instr'),'PAGE');r._r.addnext(fld)
 return d
def md(d,text,table_log):
 lines=text.splitlines();i=0;block=[]
 def flush():
  if block:d.add_paragraph(plain(' '.join(block)));block.clear()
 while i<len(lines):
  line=lines[i].strip()
  if line.startswith('|'):
   flush();rows=[]
   while i<len(lines) and lines[i].strip().startswith('|'):
    vals=[plain(x.strip()) for x in lines[i].strip().strip('|').split('|')]
    if not all(re.fullmatch(r':?-+:?',v.replace(' ','')) for v in vals):rows.append(vals)
    i+=1
   if rows:
    table_log.append('Evidence table: '+', '.join(rows[0])[:110]);d.add_paragraph(f'Table {len(table_log)}. {table_log[-1]}','Caption');t=d.add_table(rows=0,cols=max(map(len,rows)));t.style='Light Shading Accent 1'
    for vals in rows:
     cells=t.add_row().cells
     for c,v in zip(cells,vals):
      c.text=v
      for p in c.paragraphs:
       for r in p.runs:r.font.size=Pt(8)
    # Repeat table header and allow long data tables to span pages.
    trPr=t.rows[0]._tr.get_or_add_trPr();repeat=OxmlElement('w:tblHeader');trPr.append(repeat)
   continue
  if not line:flush()
  elif line.startswith('#'):flush();d.add_heading(plain(line.lstrip('# ')),level=2)
  elif line.startswith('```'):flush()
  elif re.match(r'^[-*] ',line):flush();d.add_paragraph(plain(line[2:]),style='List Bullet')
  elif line.startswith('!['):flush()
  else:block.append(line)
  i+=1
 flush()
def report():
 d=base();d.add_heading(DATA['title'],0);d.add_paragraph('Final academic project report • Phase 16')
 for x in ['Student name: [EDIT STUDENT NAME]','Registration number: [EDIT REGISTRATION NUMBER]','Institution / department: [EDIT INSTITUTION]','Supervisor: [EDIT SUPERVISOR]','Submission date: [EDIT DATE]']:d.add_paragraph(x)
 d.add_paragraph('Administrative fields are intentionally editable. No certification, signature, publication acceptance or institutional approval is asserted.')
 d.add_page_break();d.add_heading('Abstract',1);d.add_paragraph(DATA['abstract']);d.add_paragraph('Keywords: '+DATA['keywords'])
 d.add_heading('Reading and evidence conventions',2);d.add_paragraph('This report synthesizes the accepted project reports. Its source Markdown and JSON preserve the underlying text. Counts, protocols and thresholds are reported separately; archived repository paths are reproducibility references. Numerical chart images are copied without altering their data. Architecture diagrams describe information flow and contain no illustrative performance claims.')
 d.add_page_break();d.add_heading('Table of contents',1)
 for n,s in enumerate(DATA['sections'],1):d.add_paragraph(f'{n}. {s["title"]}')
 d.add_paragraph('Use the PDF bookmarks or document Navigation pane for direct chapter navigation. The editable source headings supply a regenerable contents structure.')
 d.add_page_break();d.add_heading('List of figures',1)
 figs=[im for s in DATA['sections'] for im in s['images']]
 for n,im in enumerate(figs,1):d.add_paragraph(f'Figure {n}. '+im['name'].replace('_',' ').capitalize())
 # Derive table titles from precisely the same parser used in the body.
 scratch=base();tables=[]
 for s in DATA['sections']:md(scratch,s['text'],tables)
 d.add_heading('List of tables',1)
 for n,t in enumerate(tables,1):d.add_paragraph(f'Table {n}. {t}')
 ts=[];fn=0
 for n,s in enumerate(DATA['sections'],1):
  d.add_heading(f'{n}. {s["title"]}',1);md(d,s['text'],ts)
  for im in s['images']:
   fn+=1;d.add_picture(str(ROOT/im['path']),width=Inches(6.25));d.add_paragraph(f'Figure {fn}. '+im['name'].replace('_',' ').capitalize()+'. Source: '+im['source'],'Caption')
 d.core_properties.title=DATA['title'];d.core_properties.subject='Verified Phase 16 academic synthesis';d.save(OUT/'project_report.docx')
 (OUT/'sources/document_structure.json').write_text(json.dumps(dict(chapters=len(DATA['sections']),figures=len(figs),tables=len(tables),words=len((OUT/'sources/project_report.md').read_text().split())),indent=2))

def tex(s):
 s=unicodedata.normalize('NFKD',s).encode('ascii','ignore').decode()
 return s.replace('\\','/').replace('&',r'\&').replace('%',r'\%').replace('_',r'\_').replace('#',r'\#').replace('$',r'\$').replace('~',r'\textasciitilde{}')
def manuscript():
 # Select a coherent narrative and preserve complete paragraphs, avoiding incompatible cohort pooling.
 sections={s['title']:s['text'] for s in DATA['sections']}
 selected=[('Introduction',['Introduction','Problem statement','Motivation']),('Related Work',['Literature review and related work']),('Research Contributions',['Research contributions']),('Methodology',['Proposed system','System architecture','Research objectives']),('Experimental Design',['Research gaps']),('Discussion',['Conclusion','Future work']),('Threats to Validity',['Scientific and technical limitations'])]
 text=r'''\documentclass[conference]{IEEEtran}
\usepackage[T1]{fontenc}
\usepackage[utf8]{inputenc}
\usepackage{graphicx,booktabs,amsmath,amssymb,url}
\title{Large-Scale Cyberattack Detection and Evolving Attack Pattern Mining: A Leakage-Aware Evaluation of Generalization, Drift and Adaptive Learning}
\author{\IEEEauthorblockN{[EDIT STUDENT NAME]}\IEEEauthorblockA{[EDIT DEPARTMENT AND INSTITUTION]\\{}[EDIT CITY, COUNTRY AND EMAIL]}}
\begin{document}\maketitle
\begin{abstract}'''+tex(DATA['abstract'])+r'''\end{abstract}
\begin{IEEEkeywords}intrusion detection, leakage-aware evaluation, Spark, drift, adaptive learning\end{IEEEkeywords}
'''
 def para(t):
  t=plain(t)
  keys=['spark','mllib','forest','boosting','fpgrowth','adwin','drift','cicids','pr','shap','tesseract','unb']
  t=tex(t)
  t=re.sub(r'\[([0-9,]+)\]',lambda m:r'\cite{'+','.join(keys[int(i)-1] for i in m[1].split(','))+'}',t)
  return t+'\n\n'
 for title,names in selected[:5]:
  text+='\\section{'+title+'}\n'
  for name in names:text+=para(sections[name])
 text+=r'''\subsection{Population and representation contracts}
The source release contains 16,232,943 flows, including 13,484,708 benign and 2,748,235 attack rows. Fourteen capture-only timestamp flags yield a different strict population of 16,232,929; this is not a second estimate of the same inclusion rule. Typed numerical features are audited for finite values, malformed inputs and zero denominators. Learned imputation, signed logarithms where specified, centering, scaling and estimators are fitted on training roles only. The full archived inference contract uses 18 ordered features; the separate external experiment retrains conditional common-feature baselines with only three features. These models must not be described as the same transfer experiment.

Protocol A uses grouped-random roles; B uses chronological capture roles with cross-role duplicate purging; C evaluates an unseen-family setting. Their final train/validation/test populations are respectively 11,455,925/2,344,726/2,432,292; 13,191,622/1,151,256/980,109; and 13,522,722/392,902/1,458,218. Purged counts are zero, 909,956 and 859,101. The retained B-role union is 15,322,987 and supplies a 49-batch historical replay. Training samples are independently reported rather than mislabeled as the full training population.

\subsection{Scores, decisions and comparison units}
For a threshold $\tau$, $\hat y=\mathbb{1}[s(x)\geq\tau]$, recall is $TP/(TP+FN)$ and the benign false-positive rate is $FP/(FP+TN)$. Undefined denominators remain undefined. A model's precision--recall curve summarizes ranking across thresholds; it does not establish usefulness at a frozen operating point. Thresholds are selected on validation roles and then frozen. Target-test labels are not used to tune external decisions. K-Means distance and hybrid novelty scores are not calibrated attack probabilities.

The external AUC implementation uses 2,048 bins, a step precision--recall integral and trapezoidal ROC integral. These are documented approximations, not exact continuous-score integrals. Comparing these values with unrelated implementations requires checking tie handling and binning. Neither accuracy nor an isolated AUC replaces the reported class counts and operating-point errors.

\subsection{Temporal patterns, drift and adaptation}
FP-growth mines six discretized feature items per flow, and association rules express conditional support and confidence rather than causal influence. Support sensitivity is evaluated at fixed full-source population. Emerging patterns compare declared captures; capture composition and attack prevalence can confound apparent emergence. Historical observations are distinguished from controlled synthetic changes, for which episode targets permit detection and delay accounting.

Adaptive replay predicts before labels are released. Delayed labels enter only the permitted update window; calibration and candidate promotion follow the declared policy. A candidate trained in a window cannot retroactively change that window's predictions. Cooldown, training budgets, rolling history and incumbent retention are explicit constraints. This simulated availability protocol is scientifically narrower than prospective online adaptation.

\begin{figure}[t]\centering\includegraphics[width=\columnwidth]{../figures/leakage_splitting.png}\caption{Information boundaries for role assignment and evaluation. This conceptual diagram contains no performance measurements.}\label{fig:split}\end{figure}

\section{Results}
\subsection{Leakage-aware generalization}
The random-forest group-sample baseline achieves attack recall 0.828169 on protocol A. Chronological B recall is approximately 0.0020 and unseen-family C recall approximately 0.0243. These are different test populations and should not be averaged into a single headline score. The A result supports a within-design discrimination claim, while the B and C results reveal a major generalization limitation. Randomly grouped performance is therefore insufficient evidence for future deployment.

The hybrid study combines calibrated supervised and novelty routes but does not consistently dominate all baselines. The selected B OR-fusion policy has zero attack recall at its archived operating point, despite a very small false-positive rate. This is a negative result, not a missing positive result to be replaced by post-hoc threshold selection. Family-stage diagnostics are conditional on binary routing: a correct family classifier cannot recover an attack already rejected by the binary detector. Research-only multiclass and hybrid components are consequently excluded from the portable dashboard's supported inference list.

\subsection{Frequent patterns and drift}
At minimum supports 0.10, 0.05, 0.02 and 0.01, the full-source FP-growth runs produce respectively 203, 298, 539 and 759 itemsets and 468, 629, 1,009 and 1,428 rules. The primary export retains 500 of 629 rules under the declared export bound; 20 selected rules receive independent count checks. Lower support increases the output search space, rather than proving more security-relevant knowledge. Rule interpretation remains descriptive and subject to the feature binning and capture mix.

ADWIN detects 24 of 27 targeted controlled episodes with zero stationary alarms across 11,520 eligible checks. Page--Hinkley detects 18/27 and KSWIN 17/27 with seven stationary false alarms. DDM's 6/6 result belongs to a distinct error-stream target set and cannot be ranked directly against the 27-episode feature-stream results. Historical analysis supports 45 of 49 windows; historical concept-drift ground truth is absent. Thus controlled detection sensitivity and retrospective capture shifts answer different questions.

\subsection{Adaptive learning and explanations}
On the primary 1,997,636-row adaptive evaluation, frozen P0 records 463 true positives and 4,691 false positives, approximately 0.00183 recall and 0.00269 FPR. P2 increases true positives to 634 but false positives to 9,835, approximately 0.00250 recall and 0.00564 FPR. P6 retains its incumbent and matches P0. These outcomes show a limited recall gain with a material false-positive trade-off, not unconditional adaptation success. The broader archive includes 288 synthetic experiments and 33 unique historical pipelines; these scope counts do not constitute 321 independent prospective trials.

Exact linear SHAP is reconstructed in log-odds across 48 variants. For the supported linear contract, the sum of base value and feature contributions reproduces the modeled output in its declared link space. It does not establish causal importance, and log-odds contributions must not be displayed as additive probabilities. Direct interventional tree SHAP for the archived PySpark trees remains unsupported. The accepted interface therefore exposes validated linear explanations and explicit unavailability rather than a fabricated tree explanation.

\subsection{Conditional external validation}
The CICIDS2017 mirror has eight CSV files totaling 884,645,759 bytes at pinned version 1. After eligibility rules, it supplies 2,830,743 rows: 2,273,097 benign and 557,646 attack. The chronological test has 308,939 rows, of which 129,275 are attacks and 179,664 benign. Collision exclusions number 287,528 in this protocol; the distinct grouped test contains 508,641 rows with 218,235 exclusions. These populations must not be combined. Exact upstream extractor builds and official-archive byte identity remain unverified.

Table~\ref{tab:external} reports primary chronological decisions. The source common-feature LR detects no attacks; source RF transfers some ranking signal but its source-validation operating threshold incurs a 4.254\% external benign FPR. A target-trained chronological RF achieves 5.436\% recall at its calibrated low-FPR threshold. Its fixed 0.5 threshold instead achieves 64.954\% recall and 1.722\% FPR. That contrast demonstrates threshold sensitivity, not permission to choose whichever test threshold looks best. The common-feature source models are newly trained three-feature baselines, not the exact archived 18-feature models.

\begin{table}[t]\caption{Primary external chronological test: 129,275 attacks and 179,664 benign rows. Validation-calibrated thresholds.}\label{tab:external}\centering\small
\begin{tabular}{lrrrr}\toprule Model & TP & FP & Recall & FPR\\\midrule Source LR &0&0&0&0\\Source RF&14,459&7,643&.11185&.04254\\Target LR&0&229&0&.00127\\Target RF&7,028&70&.05436&.00039\\\bottomrule\end{tabular}\end{table}

\subsection{Measured execution and usable inference}
Volume and worker experiments contain 48 measured and 16 warm-up runs, using actual populations 1,000,860, 3,998,178, 7,998,515 and 16,232,943. A four-worker setting is not consistently faster. The full-volume three-worker transform median is 21.076 seconds. These local-thread observations cannot establish multi-node scaling efficiency, resilience or production throughput.

In the matched one-million-row comparison, median end-to-end Pandas time is 0.242245 seconds and Spark 0.616481 seconds. Spark is therefore slower for this measured small workload, despite its broader distributed capabilities. Storage and workload consumption matter: the recorded full numeric Parquet artifact is 116,203,334 bytes with a 0.626799-second read median, versus 217,833,168-byte CSV and 1.921769 seconds. Different actions, caching and parsing costs must not be silently combined into a universal speedup.

The final advanced dashboard exposes 13 modules over nine navigation areas, 203 evidence tables and three portable models: LR, RF and K-Means. Its accepted 2,445-probe parity suite contains 100 LR, 2,245 RF and 100 K-Means probes. Maximum LR/RF probability deviations are approximately $1.53\times10^{-16}$ and $1.11\times10^{-16}$; maximum K-Means distance deviation is $4.37\times10^{-11}$. This establishes fidelity of bounded reconstruction, not additional predictive validity. Uploads are limited to 1 MiB and 500 rows, use the exact ordered feature schema, and retain invalid-row diagnostics. Manual and uploaded values use training medians; no transform is refitted on user input.

'''
 for title,names in selected[5:]:
  text+='\\section{'+title+'}\n'
  for name in names:text+=para(sections[name])
 text+=r'''\subsection{Reproducibility and evidence boundaries}
The evidence matrix links each completed research phase to a full Git checkpoint and report hash. The master results table adds exact row selectors and metric denominators. Compact aggregate outputs and portable parameters are versioned, while raw private inputs and credentials are excluded. The final academic package provides editable sources, diagrams, presentation, viva preparation and file hashes; recomputing private Spark experiments requires separately authorized source access and pinned runtime components.

There is no claim that these artifacts constitute an independently replicated clinical, operational or prospective security trial. Repeated runs estimate execution variability within the measured environment, not independent dataset uncertainty. Capture dependence, mirror provenance, sparse family distributions, binning choices, label delays and threshold-selection rules all limit extrapolation. A public dashboard deployment would be a separate administrative action, not evidence that the detector is safe for live automated response.

\section{Conclusion}
This case study shows why leakage controls, temporal roles, label availability and threshold decisions must accompany model scores. Grouped-random detection can coexist with poor chronological recall; associations and controlled drift alarms do not establish historical causal changes; and adaptation may buy small recall gains at substantial false-positive cost. Conditional external validation and matched local execution measurements expose further limits rather than erasing them. The defensible contribution is a traceable integrated evaluation and faithful inference demonstration. Future work requires stronger compatible provenance, prospective labels, independently calibrated operating budgets and multi-node measurements before broader effectiveness claims are justified.
\bibliographystyle{ieeetr}\bibliography{references}
\end{document}
'''
 fragment=OUT/'manuscript/methodology_detail.tex'
 if fragment.exists():text=text.replace(r'\section{Results}',fragment.read_text()+'\n'+r'\section{Results}')
 (OUT/'manuscript/manuscript.tex').write_text(text)
 # ASCII transliteration only for TeX compatibility; canonical metadata remains in the audit JSON.
 bp=OUT/'manuscript/references.bib';bp.write_text(unicodedata.normalize('NFKD',bp.read_text()).encode('ascii','ignore').decode())
if __name__=='__main__':report();manuscript();print('DOCX and IEEE sources built')
