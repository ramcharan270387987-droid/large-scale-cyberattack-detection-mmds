"""Genuine integrated browser,inference,upload,download and mobile acceptance."""
import json,re,time,hashlib,sys
from pathlib import Path
import pandas as pd
from playwright.sync_api import sync_playwright
from src.interactive import evidence,portable,inputs
from dashboard.advanced_app import FILTERS
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'reports/phase15_validation'
def choose(page,label,value):
    control=page.get_by_role('combobox',name=re.compile('^'+re.escape(label)+'$'))
    if control.input_value()==str(value):return
    control.click();control.fill(str(value));page.get_by_role('option',name=str(value),exact=True).click();page.wait_for_timeout(350)
def workspace(page,name):choose(page,'Workspace',name);page.get_by_role('heading',name=name,exact=True).wait_for()
def main():
    start=time.monotonic();errors=[];http=[];sections=[];models=[];screens=[];OUT.mkdir(exist_ok=True)
    with sync_playwright() as p:
        browser=p.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--no-sandbox']);context=browser.new_context(viewport={'width':1440,'height':1100},accept_downloads=True);page=context.new_page();page.on('pageerror',lambda e:errors.append(str(e)));page.on('response',lambda r:http.append(r.status) if r.status>=400 else None);page.on('console',lambda m:errors.append(m.text) if m.type=='error' else None)
        page.goto('http://127.0.0.1:8515');page.get_by_role('heading',name='Executive overview',exact=True).wait_for();shot=OUT/'overview-desktop.png';page.screenshot(path=str(shot),full_page=True);screens.append(shot.name)
        resume='--resume' in sys.argv
        if resume:sections=json.loads((OUT/'browser-areas.json').read_text())
        for group,entries in ([] if resume else evidence.catalog()['groups'].items()):
            workspace(page,group);entry=entries[0];data=evidence.load(entry);filters=[]
            for col in FILTERS:
                if col not in data or not data[col].map(lambda x:not isinstance(x,(dict,list,tuple,set)) and (isinstance(x,(str,int,float,bool)) or pd.isna(x))).all():continue
                choices=sorted(data[col].dropna().unique().tolist(),key=str)
                if 1<len(choices)<=100:
                    value=choices[-1];choose(page,col.replace('_',' ').capitalize(),value);data=data[data[col].eq(value)];filters.append(col)
            expected=data.to_csv(index=False).encode();token=hashlib.sha256(expected).hexdigest()[:16];page.get_by_text('Evidence ID: '+token,exact=False).wait_for();button=page.locator('.st-key-research_'+token).get_by_role('button',name='Download research CSV',exact=True);button.wait_for();page.wait_for_timeout(200)
            with page.expect_download() as event:button.click()
            dest=OUT/('download-area-'+str(len(sections))+'.csv');event.value.save_as(str(dest));assert dest.read_bytes()==expected,group;sections.append(dict(group=group,entry=entry['path'],filters=filters,evidence_id=token,rows=len(data),download_sha256=hashlib.sha256(expected).hexdigest()))
        (OUT/'browser-areas.json').write_text(json.dumps(sections,indent=2)+'\n')
        workspace(page,'Interactive inference')
        for entry in evidence.models():
            choose(page,'Executable model',entry['kind']+' · '+entry['id']);page.get_by_role('button',name='Run inference',exact=True).click();model=portable.verify(ROOT/entry['artifact'],entry['sha256']);expected=portable.predict(model,dict.fromkeys(model['features'],None));page.get_by_text(expected['label'],exact=True).wait_for();page.get_by_role('heading',name='Computed prediction',exact=True).wait_for()
            if entry['kind'] in ('LR','KMeans'):page.get_by_role('heading',name='Exact prediction explanation',exact=True).wait_for()
            models.append(dict(id=entry['id'],manual_label=expected['label'],manual_score=expected.get('probability',expected.get('squared_distance')),status='PASS'))
            if entry['kind']=='LR':shot=OUT/'inference-desktop.png';page.screenshot(path=str(shot),full_page=True);screens.append(shot.name)
        # Invalid manual feature is reported without generating a prediction.
        page.get_by_role('textbox',name='flow_duration',exact=True).fill('-1');page.get_by_role('button',name='Run inference',exact=True).click();page.get_by_text('Feature outside finite',exact=False).wait_for()
        page.get_by_text('CSV batch',exact=True).click();uploader=page.get_by_test_id('stFileUploader').locator('input[type=file]');uploader.set_input_files(str(ROOT/'dashboard/data/phase15_demo.csv'));page.get_by_text('Upload ID: '+hashlib.sha256((ROOT/'dashboard/data/phase15_demo.csv').read_bytes()).hexdigest()[:16],exact=True).wait_for();page.get_by_role('button',name='Predict CSV',exact=True).click();page.get_by_role('button',name='Download predictions',exact=True).wait_for();page.get_by_text('Computed explanation for uploaded logical row 1',exact=True).wait_for();page.wait_for_timeout(300)
        entry=evidence.models()[-1];model=portable.verify(ROOT/entry['artifact'],entry['sha256']);demo=(ROOT/'dashboard/data/phase15_demo.csv').read_bytes();expected=inputs.safe_csv(inputs.batch(model,inputs.parse_csv(demo,model['features'])))
        with page.expect_download() as event:page.get_by_role('button',name='Download predictions',exact=True).click()
        event.value.save_as(str(OUT/'predictions-demo.csv'));assert (OUT/'predictions-demo.csv').read_bytes()==expected
        mixed=demo+b'bad,'+b','.join([b'0']*17)+b'\n';uploader.set_input_files({'name':'mixed.csv','mimeType':'text/csv','buffer':mixed});page.get_by_text('Upload ID: '+hashlib.sha256(mixed).hexdigest()[:16],exact=True).wait_for();page.get_by_role('button',name='Predict CSV',exact=True).click();page.get_by_text('Invalid rows retained',exact=True).wait_for();page.get_by_role('button',name='Download predictions',exact=True).wait_for();page.get_by_text('Computed explanation for uploaded logical row 1',exact=True).wait_for();page.wait_for_timeout(300)
        with page.expect_download() as event:page.get_by_role('button',name='Download predictions',exact=True).click()
        event.value.save_as(str(OUT/'predictions-mixed.csv'));assert (OUT/'predictions-mixed.csv').read_bytes()==inputs.safe_csv(inputs.batch(model,inputs.parse_csv(mixed,model['features'])))
        uploader.set_input_files({'name':'wrong.csv','mimeType':'text/csv','buffer':b'wrong\n1\n'});page.get_by_text('Upload ID: '+hashlib.sha256(b'wrong\n1\n').hexdigest()[:16],exact=True).wait_for();page.get_by_role('button',name='Predict CSV',exact=True).click();page.get_by_text('CSV schema/order mismatch',exact=False).wait_for()
        # Actual missing-artifact state,restored even if a browser assertion fails.
        target=ROOT/entry['artifact'];backup=target.with_suffix('.json.unavailable');target.rename(backup)
        try:
            page.reload();workspace(page,'Interactive inference');choose(page,'Executable model',entry['kind']+' · '+entry['id']);page.get_by_text('Model unavailable or checksum invalid',exact=False).wait_for()
        finally:backup.rename(target)
        workspace(page,'Historical replay');choose(page,'Capture',sorted(pd.read_csv(ROOT/'reports/phase6_replay_batches.csv').source_day.unique())[-1]);page.get_by_role('heading',name='Archived detection and novelty summary',exact=True).wait_for();shot=OUT/'replay-desktop.png';page.screenshot(path=str(shot),full_page=True);screens.append(shot.name)
        workspace(page,'Evidence & reproducibility');page.get_by_role('button',name='Download document',exact=True).wait_for();page.get_by_role('button',name='Download figure',exact=True).wait_for()
        mobile=browser.new_context(viewport={'width':390,'height':844},is_mobile=True);m=mobile.new_page();m.on('pageerror',lambda e:errors.append(str(e)));m.goto('http://127.0.0.1:8515');m.get_by_role('heading',name='Executive overview',exact=True).wait_for();shot=OUT/'overview-mobile.png';m.screenshot(path=str(shot),full_page=True);screens.append(shot.name)
        # Streamlit sidebar is collapsed on mobile;open it for navigation.
        toggle=m.get_by_test_id('stExpandSidebarButton')
        if toggle.count():toggle.click()
        workspace(m,'Interactive inference')
        collapse=m.get_by_test_id('stSidebarCollapseButton')
        if collapse.count():collapse.click()
        m.get_by_role('button',name='Run inference',exact=True).click();m.get_by_role('heading',name='Computed prediction',exact=True).wait_for();overflow=m.evaluate("() => {let e=document.querySelector('[data-testid=stMain]');return e.scrollWidth>e.clientWidth+2}");assert not overflow
        shot=OUT/'inference-mobile.png';m.screenshot(path=str(shot),full_page=True);screens.append(shot.name);mobile.close();context.close();browser.close()
    assert not errors,errors
    assert not http,http
    r=dict(status='PASS',research_areas=sections,manual_models=models,valid_csv_rows=3,mixed_csv_rows=4,invalid_csv=True,manual_invalid=True,prediction_downloads_verified=True,uploaded_row_explanation=True,model_unavailable=True,replay=True,provenance=True,mobile_horizontal_main_overflow=False,screenshots=screens,page_errors=errors,http_errors=http,seconds=time.monotonic()-start,resumed_research_areas=resume);(OUT/'browser.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r))
if __name__=='__main__':main()
