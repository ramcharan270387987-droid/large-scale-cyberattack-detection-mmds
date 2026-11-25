"""Settled Chromium evidence/download identity and desktop/mobile audit."""
import json,re,time,hashlib
from pathlib import Path
import pandas as pd
from playwright.sync_api import sync_playwright
from dashboard import phase14_preview as ui
ROOT=Path(__file__).resolve().parents[1];DEST=ROOT/'reports/phase14_validation'
def choose(page,label,value):
    combo=page.get_by_role('combobox',name=re.compile(re.escape(label)+r'$'));combo.click();combo.fill(str(value));page.get_by_role('option',name=str(value),exact=True).click();page.wait_for_timeout(250)
    status=page.get_by_test_id('stStatusWidget')
    if status.count():
        try:status.wait_for(state='hidden',timeout=20000)
        except Exception:pass

def main():
    errors=[];http=[];results=[];screens=[];start=time.monotonic();DEST.mkdir(exist_ok=True)
    with sync_playwright() as p:
        browser=p.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--no-sandbox']);context=browser.new_context(viewport={'width':1440,'height':1050},accept_downloads=True);page=context.new_page();page.on('pageerror',lambda e:errors.append(str(e)));page.on('response',lambda r:http.append(r.status) if r.status>=400 else None);page.on('console',lambda m:errors.append(m.text) if m.type=='error' else None)
        page.goto('http://127.0.0.1:8514');page.get_by_role('heading',name='External Validation and Scalability Laboratory',exact=True).wait_for()
        for section,filename in ui.SECTIONS.items():
            choose(page,'Evidence',section);data=pd.read_csv(ROOT/'reports'/filename);exercised=[]
            for column in ui.FILTERS:
                if column not in data:continue
                choices=sorted(data[column].dropna().unique().tolist())
                if not choices:continue
                value=choices[-1];label=ui.LABELS.get(column,column.replace('_',' ').capitalize());choose(page,label,value);data=ui.select(data,column,value);exercised.append(label)
            expected=ui.csv_bytes(data);identity=hashlib.sha256(expected).hexdigest()[:16]
            page.get_by_text('Evidence ID: '+identity,exact=False).wait_for();page.get_by_test_id('stDataFrame').wait_for()
            with page.expect_download() as event:page.get_by_role('button',name='Download filtered CSV',exact=True).click()
            path=DEST/('download-'+filename);event.value.save_as(str(path));assert path.read_bytes()==expected,(section,'CSV differs from visible evidence')
            results.append(dict(section=section,status='PASS',filters=exercised,download_rows=len(data),evidence_id=identity,download_sha256=hashlib.sha256(expected).hexdigest()))
            if section=='External model comparison':
                shot=DEST/'preview-desktop.png';page.screenshot(path=str(shot),full_page=True);screens.append(shot.name)
        choose(page,'Evidence','Research limitations');page.get_by_role('heading',name='Phase14 scientific limitations').wait_for()
        choose(page,'Evidence','Study figures');page.get_by_test_id('stImage').wait_for()
        for format in ('PNG','SVG'):
            choose(page,'Download format',format)
            with page.expect_download() as event:page.get_by_role('button',name='Download figure',exact=True).click()
            assert event.value.suggested_filename.endswith('.'+format.lower())
        mobile=browser.new_context(viewport={'width':390,'height':844},is_mobile=True);m=mobile.new_page();m.on('pageerror',lambda e:errors.append(str(e)));m.goto('http://127.0.0.1:8514');m.get_by_role('heading',name='External Validation and Scalability Laboratory',exact=True).wait_for();choose(m,'Evidence','External confusion matrices');m.get_by_test_id('stDataFrame').wait_for();overflow=m.evaluate("() => {let e=document.querySelector('[data-testid=stMain]');return e.scrollWidth>e.clientWidth+2}");assert not overflow
        shot=DEST/'preview-mobile.png';m.screenshot(path=str(shot),full_page=True);screens.append(shot.name);mobile.close();context.close();browser.close()
    assert not errors,errors
    assert not http,http
    receipt=dict(status='PASS',sections=results,download_hashes_verified=True,figure_downloads=['PNG','SVG'],screenshots=len(screens),screenshot_files=screens,mobile_horizontal_main_overflow=False,page_errors=errors,http_errors=http,seconds=time.monotonic()-start,browser='Chromium / Playwright',scope='isolated local preview; public dashboard unchanged')
    (DEST/'browser.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(receipt))
if __name__=='__main__':main()
