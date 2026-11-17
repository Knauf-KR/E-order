"""Keep the browser mockup and Power Fx UI-only collection aligned with sample JSON."""
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def fx(v,kind):
    if v is None:return 'Blank()'
    if kind=='Boolean':return 'true' if v else 'false'
    if kind=='Number':return str(v)
    if kind=='Date':return 'Date('+','.join(str(int(x)) for x in v.split('-'))+')'
    return '"'+str(v).replace('"','""').replace('\r',' ').replace('\n',' ')+'"'
def build():
    rows=json.loads((ROOT/'sample/assets_ready.sample.json').read_text())
    stage=json.loads((ROOT/'sample/staging.sample.json').read_text())
    fields=next(x['fields'] for x in json.loads((ROOT/'schema/sharepoint-lists.json').read_text())['lists'] if x['name']=='ITAssets')
    browser=[];parts=[]
    for idx,row in enumerate(rows,1):
        b=dict(row,ID=idx);b.pop('LegacyMetadata',None);browser.append(b)
        values=['ID: '+str(idx)]
        for f in fields:values.append(f['name']+': '+fx('' if f['name']=='LegacyMetadata' else row.get(f['name']),f['type']))
        parts.append('{'+', '.join(values)+'}')
    (ROOT/'prototype/sample-data.js').write_text('window.sampleAssets = '+json.dumps(browser,ensure_ascii=False)+';\nwindow.sampleReviewCount = '+str(sum(r['ReviewState']!='Ready' for r in stage))+';\n',encoding='utf-8')
    (ROOT/'powerfx/11_Sample.Init.fx').write_text('// Fictional UI-only records. IDs are temporary; never use them as SharePoint IDs.\nClearCollect(colSampleAssets,\n'+',\n'.join(parts)+'\n);\nClearCollect(colSnapshot,colSampleAssets); Set(varSnapshotComplete,true)\n',encoding='utf-8')
if __name__=='__main__':build()
