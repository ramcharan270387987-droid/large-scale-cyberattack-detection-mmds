"""Actual Chromium UI audit of isolated preview, with downloaded CSV checks."""
import ast,csv,json,re,sys,time
from pathlib import Path
import pandas as pd
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[1];DEST=ROOT/'reports/phase12_validation'
module=ast.parse((ROOT/'dashboard/phase12_preview.py').read_text())
values={node.targets[0].id:ast.literal_eval(node.value) for node in module.body if isinstance(node,ast.Assign) and isinstance(node.targets[0],ast.Name) and node.targets[0].id in ('SECTIONS','FILTERS','LABELS')}
SECTIONS=values['SECTIONS'];FILTERS=values['FILTERS'];LABELS=values['LABELS']

def choose(page,label,value):
    combo=page.get_by_role('combobox',name=re.compile(re.escape(label)+r'$'))
    combo.click();combo.fill(str(value));page.get_by_role('option',name=str(value),exact=True).click()
    page.wait_for_timeout(180)
    status=page.get_by_test_id('stStatusWidget')
    if status.count():
        try:status.wait_for(state='hidden',timeout=15000)
        except Exception:pass

def main():
    DEST.mkdir(exist_ok=True);errors=[];http=[];results=[];screens=[];start=time.monotonic()
    with sync_playwright() as p:
        browser=p.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--no-sandbox'])
        context=browser.new_context(viewport={'width':1440,'height':1050},accept_downloads=True)
        page=context.new_page();page.on('pageerror',lambda e:errors.append(str(e)))
        page.on('console',lambda msg:errors.append('console: '+msg.text) if msg.type=='error' else None)
        page.on('response',lambda r:http.append({'url':r.url,'status':r.status}) if r.status>=400 else None)
        page.goto('http://127.0.0.1:8512');page.get_by_role('heading',name='Adaptive Learning and Model Registry',exact=True).wait_for()
        for section,filename in SECTIONS.items():
            choose(page,'Evidence',section)
            path=ROOT/'reports'/filename
            assert path.exists(),('missing delivered evidence',section)
            data=pd.read_csv(path)
            if section.startswith('Synthetic') and 'backend' in data:data['mechanism']=data.backend.str.split('-seed').str[0]
            if section=='Model history':data=data.rename(columns={'family':'model_family'})
            if section=='Family exposure and forward support':data=data.rename(columns={'period':'exposure_period'})
            assert not data.empty,('unexpected unsupported whole section',section)
            page.get_by_test_id('stDataFrame').wait_for()
            if section=='Static versus adaptive comparison':
                shot=DEST/'preview-desktop.png';page.screenshot(path=str(shot),full_page=True);screens.append(shot.name)
            exercised=[]
            for column in FILTERS:
                if column not in data:continue
                choices=sorted(data[column].dropna().unique().tolist())
                if not choices:continue
                value=choices[-1]
                label=LABELS.get(column,column.replace('_',' ').capitalize())
                choose(page,label,value);data=data.loc[data[column].eq(value)];exercised.append(label)
            page.get_by_test_id('stDataFrame').wait_for()
            with page.expect_download() as event:page.get_by_role('button',name='Download filtered CSV',exact=True).click()
            downloaded=event.value;target=DEST/('download-'+filename);downloaded.save_as(str(target))
            with target.open() as stream:actual=list(csv.DictReader(stream))
            assert len(actual)==len(data),(section,len(actual),len(data))
            if section=='Static versus adaptive comparison':
                shot=DEST/'preview-desktop-download.png';page.screenshot(path=str(shot),full_page=True);screens.append(shot.name)
            results.append({'section':section,'status':'PASS','filters':exercised,'download_records':len(actual),
                            'charts':page.get_by_test_id('stVegaLiteChart').count()})
        choose(page,'Evidence','Study figures');page.get_by_test_id('stImage').wait_for()
        choose(page,'Evidence','Synthetic benchmark');page.get_by_test_id('stDataFrame').wait_for()
        choose(page,'Policy','P2');choose(page,'ADWIN sensitivity',True)
        with page.expect_download() as probe:page.get_by_role('button',name='Download filtered CSV',exact=True).click()
        probe.value.save_as(str(DEST/'download-adwin-true.csv'))
        adwin_rows=list(csv.DictReader((DEST/'download-adwin-true.csv').open()))
        assert len(adwin_rows)==6 and all(r['advanced']=='True' for r in adwin_rows)
        choose(page,'Evidence','Research limitations');page.get_by_text('Frozen before new fitting.',exact=False).wait_for()
        results.append({'section':'Research limitations','status':'PASS'})
        choose(page,'Evidence','Study figures');page.get_by_test_id('stImage').wait_for()
        with page.expect_download() as event:page.get_by_role('button',name='Download figure',exact=True).click()
        assert event.value.suggested_filename.endswith('.png')
        results.append({'section':'Study figures','status':'PASS','figure_download':True})
        mobile=browser.new_context(viewport={'width':390,'height':844},is_mobile=True,device_scale_factor=1)
        m=mobile.new_page();m.on('pageerror',lambda e:errors.append(str(e)));m.on('console',lambda msg:errors.append('console: '+msg.text) if msg.type=='error' else None);m.goto('http://127.0.0.1:8512')
        m.get_by_role('heading',name='Adaptive Learning and Model Registry',exact=True).wait_for()
        choose(m,'Evidence','Synthetic benchmark');m.get_by_test_id('stDataFrame').wait_for()
        overflow=m.evaluate("() => {const e=document.querySelector('[data-testid=stMain]');return e.scrollWidth>e.clientWidth+2}")
        assert not overflow,'Mobile main content overflow'
        shot=DEST/'preview-mobile.png';m.screenshot(path=str(shot),full_page=True);screens.append(shot.name)
        m.get_by_role('button',name='Download filtered CSV',exact=True).scroll_into_view_if_needed()
        shot=DEST/'preview-mobile-results.png';m.screenshot(path=str(shot),full_page=True);screens.append(shot.name)
        mobile.close();context.close();browser.close()
    assert not errors,errors
    assert not http,http
    receipt={'status':'PASS','browser':'Chromium / Playwright','url':'http://127.0.0.1:8512','sections':results,
             'screenshots':len(screens),'screenshot_files':screens,'desktop':[1440,1050],'mobile':[390,844],
             'adwin_sensitivity_download_records':len(adwin_rows),'mobile_horizontal_main_overflow':False,'page_errors':errors,'http_errors':http,'seconds':time.monotonic()-start,
             'scope':'isolated local preview; protected public dashboard unchanged'}
    (DEST/'browser.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(receipt))
if __name__=='__main__':main()
