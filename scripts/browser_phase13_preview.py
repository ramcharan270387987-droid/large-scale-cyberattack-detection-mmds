"""Chromium audit of all Phase13 aggregate sections, filtered downloads and mobile."""
import ast,csv,json,re,time
from pathlib import Path
import pandas as pd
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[1];DEST=ROOT/'reports/phase13_validation'
module=ast.parse((ROOT/'dashboard/phase13_preview.py').read_text());v={n.targets[0].id:ast.literal_eval(n.value) for n in module.body if isinstance(n,ast.Assign) and isinstance(n.targets[0],ast.Name) and n.targets[0].id in ('SECTIONS','FILTERS','LABELS')};SECTIONS=v['SECTIONS'];FILTERS=v['FILTERS'];LABELS=v['LABELS']
def choose(page,label,value):
    c=page.get_by_role('combobox',name=re.compile(re.escape(label)+r'$'));c.click();c.fill(str(value));page.get_by_role('option',name=str(value),exact=True).click();page.wait_for_timeout(220)
    status=page.get_by_test_id('stStatusWidget')
    if status.count():
        try:status.wait_for(state='hidden',timeout=15000)
        except Exception:pass

def main():
    DEST.mkdir(exist_ok=True);errors=[];http=[];results=[];screens=[];start=time.monotonic()
    with sync_playwright() as p:
        browser=p.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--no-sandbox']);context=browser.new_context(viewport={'width':1440,'height':1050},accept_downloads=True);page=context.new_page();page.on('pageerror',lambda e:errors.append(str(e)));page.on('console',lambda m:errors.append(m.text) if m.type=='error' else None);page.on('response',lambda r:http.append(r.status) if r.status>=400 else None)
        page.goto('http://127.0.0.1:8513');page.get_by_role('heading',name='Explainability Research Laboratory',exact=True).wait_for()
        for section,filename in SECTIONS.items():
            choose(page,'Evidence',section);data=pd.read_csv(ROOT/'reports'/filename);assert not data.empty;page.get_by_test_id('stDataFrame').wait_for();exercised=[]
            if section=='Global feature importance':
                path=DEST/'preview-desktop.png';page.screenshot(path=str(path),full_page=True);screens.append(path.name)
            for column in FILTERS:
                if column not in data:continue
                values=sorted(data[column].dropna().unique().tolist())
                if not values:continue
                value=values[-1];label=LABELS.get(column,column.replace('_',' ').capitalize());choose(page,label,value);data=data.loc[data[column].eq(value)];exercised.append(label)
            page.get_by_test_id('stDataFrame').wait_for()
            with page.expect_download() as event:page.get_by_role('button',name='Download filtered CSV',exact=True).click()
            path=DEST/('download-'+filename);event.value.save_as(str(path));actual=pd.read_csv(path);assert len(actual)==len(data),(section,len(actual),len(data));results.append(dict(section=section,filters=exercised,download_records=len(actual),status='PASS'))
        choose(page,'Evidence','Scientific limitations');page.get_by_role('heading',name='Phase 13 scientific limitations').wait_for()
        choose(page,'Evidence','Study figures');page.get_by_test_id('stImage').wait_for()
        with page.expect_download() as event:page.get_by_role('button',name='Download figure',exact=True).click()
        assert event.value.suggested_filename.endswith('.png')
        mobile=browser.new_context(viewport={'width':390,'height':844},is_mobile=True);m=mobile.new_page();m.on('pageerror',lambda e:errors.append(str(e)));m.goto('http://127.0.0.1:8513');m.get_by_role('heading',name='Explainability Research Laboratory',exact=True).wait_for();choose(m,'Evidence','Local synthetic explanation');m.get_by_test_id('stDataFrame').wait_for();overflow=m.evaluate("() => {let e=document.querySelector('[data-testid=stMain]');return e.scrollWidth>e.clientWidth+2}");assert not overflow
        path=DEST/'preview-mobile.png';m.screenshot(path=str(path),full_page=True);screens.append(path.name);mobile.close();context.close();browser.close()
    assert not errors,errors
    assert not http,http
    receipt=dict(status='PASS',sections=results,screenshots=len(screens),screenshot_files=screens,mobile_horizontal_main_overflow=False,page_errors=errors,http_errors=http,seconds=time.monotonic()-start,browser='Chromium / Playwright',url='http://127.0.0.1:8513',scope='isolated local archived-evidence preview')
    (DEST/'browser.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(receipt))
if __name__=='__main__':main()
