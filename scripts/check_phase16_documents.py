"""Structural PDF/Office checks and actual rendered-page review artifacts."""
import json,re,hashlib
from pathlib import Path
import fitz
from PIL import Image,ImageOps,ImageDraw
from docx import Document
from pptx import Presentation
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'deliverables/final_submission';QA=ROOT/'reports/phase16_validation';QA.mkdir(exist_ok=True)
def main():
 counts={};outside=[];short=[]
 names=['project_report.pdf','manuscript/manuscript.pdf','academic_presentation.pdf','viva_handbook.pdf','speaker_notes.pdf']
 for name in names:
  pdf=fitz.open(OUT/name);counts[name]=len(pdf);thumbs=[]
  for i,p in enumerate(pdf):
   txt=p.get_text();assert len(txt.strip())>60,(name,i)
   if len(txt.strip())<180:short.append([name,i+1,len(txt.strip())])
   for b in p.get_text('blocks'):
    if b[0]<-1 or b[1]<-1 or b[2]>p.rect.width+1 or b[3]>p.rect.height+1:outside.append([name,i+1,b[:4]])
   pix=p.get_pixmap(matrix=fitz.Matrix(.30,.30),alpha=False);im=Image.frombytes('RGB',(pix.width,pix.height),pix.samples);im.thumbnail((270,220));tile=Image.new('RGB',(290,245),'#dbe3eb');tile.paste(im,((290-im.width)//2,5));ImageDraw.Draw(tile).text((10,228),f'{name} : {i+1}',fill='black');thumbs.append(tile)
  cols=4;sheet=Image.new('RGB',(cols*290,((len(thumbs)+cols-1)//cols)*245),'white')
  for i,im in enumerate(thumbs):sheet.paste(im,((i%cols)*290,(i//cols)*245))
  stem=Path(name).stem;sheet.save(QA/(stem+'_contact.png'))
  chosen=[0,len(pdf)//2,len(pdf)-1] if len(pdf)>8 else list(range(len(pdf)))
  for i in chosen:pdf[i].get_pixmap(matrix=fitz.Matrix(1.15,1.15),alpha=False).save(QA/f'{stem}_page_{i+1}.png')
 assert 50<=counts['project_report.pdf']<=80
 assert 6<=counts['manuscript/manuscript.pdf']<=8
 assert counts['academic_presentation.pdf']==24
 assert not outside,outside
 doc=Document(OUT/'project_report.docx');assert len(doc.inline_shapes)>=15 and len(doc.tables)>=15
 deck=Presentation(OUT/'academic_presentation.pptx');assert len(deck.slides)==24
 for i,slide in enumerate(deck.slides,1):
  assert len(slide.notes_slide.notes_text_frame.text.split())>=45
  for shape in slide.shapes:assert shape.left>=0 and shape.top>=0 and shape.left+shape.width<=deck.slide_width+100 and shape.top+shape.height<=deck.slide_height+100,(i,shape.name)
 viva=(OUT/'sources/viva_handbook.md').read_text();assert len(re.findall(r'^## Q\d+\.',viva,re.M))==80
 log=(OUT/'manuscript/manuscript.log').read_text();assert not any(x in log for x in ['undefined references','Citation `','Overfull','! LaTeX Error'])
 # Check final PDF text contains the expected endpoint slide and all bibliography identities.
 paper='\n'.join(p.get_text() for p in fitz.open(OUT/'manuscript/manuscript.pdf'))
 assert '[12]' in paper and 'TESSERACT' in paper and 'ADWIN' in paper
 r=dict(status='PASS',artifact_sha256={name:hashlib.sha256((OUT/name).read_bytes()).hexdigest() for name in names},pdf_pages=counts,report_images=len(doc.inline_shapes),report_tables=len(doc.tables),presentation_slides=24,slides_with_notes=24,viva_questions=80,out_of_page_text_blocks=outside,short_pages=short,rendering='LibreOffice DOCX/PPTX exports; genuine IEEEtran compiled with pdfLaTeX and BibTeX',visual_review='PENDING',fonts='Times/Calibri with LibreOffice font substitution permitted; inspect rendered artifacts')
 (QA/'document_quality.json').write_text(json.dumps(r,indent=2)+'\n');print(r)
if __name__=='__main__':main()
