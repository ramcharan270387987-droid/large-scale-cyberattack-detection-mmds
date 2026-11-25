"""Insert rendered page numbers into the editable report's front-matter lists."""
import re,json
from pathlib import Path
import fitz
from docx import Document
from docx.shared import Cm
from docx.enum.text import WD_TAB_ALIGNMENT,WD_TAB_LEADER
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'deliverables/final_submission'
def main():
 pdf=fitz.open(OUT/'project_report.pdf');chapters={t:p for l,t,p in pdf.get_toc() if l==1 and re.match(r'^\d+\.',t)};figs={};tables={}
 for page,p in enumerate(pdf,1):
  for n in re.findall(r'Figure (\d+)\.',p.get_text()):figs.setdefault(int(n),page)
  for n in re.findall(r'Table (\d+)\.',p.get_text()):tables.setdefault(int(n),page)
 # Front matter itself contains caption labels. Restrict to body pages.
 figs={};tables={};start=min(chapters.values())
 for page in range(start,len(pdf)+1):
  text=pdf[page-1].get_text()
  for n in re.findall(r'Figure (\d+)\.',text):figs.setdefault(int(n),page)
  for n in re.findall(r'Table (\d+)\.',text):tables.setdefault(int(n),page)
 d=Document(OUT/'project_report.docx');body=False;updates=0
 for p in d.paragraphs:
  if p.style.name=='Heading 1' and re.match(r'^1\. Introduction',p.text):body=True
  if body:continue
  title=p.text.split('\t')[0];page=chapters.get(title)
  m=re.match(r'Figure (\d+)\.',title)
  if m:page=figs.get(int(m[1]))
  m=re.match(r'Table (\d+)\.',title)
  if m:page=tables.get(int(m[1]))
  if page:
   p.text=title+'\t'+str(page);p.paragraph_format.tab_stops.add_tab_stop(Cm(16),WD_TAB_ALIGNMENT.RIGHT,WD_TAB_LEADER.DOTS);updates+=1
 d.save(OUT/'project_report.docx');r=dict(chapters=chapters,figures=figs,tables=tables,entries_updated=updates)
 (OUT/'sources/report_pagination.json').write_text(json.dumps(r,indent=2)+'\n');print('Inserted page numbers:',updates)
if __name__=='__main__':main()
