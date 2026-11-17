"""All identifiers, names, sites and dates below are fictional test data."""
from pathlib import Path
from datetime import date,timedelta
import json,csv
import openpyxl
from convert_excel import convert,SHEETS
ROOT=Path(__file__).resolve().parents[1]
BASE=date(2026,11,17)
def create(path):
    b=openpyxl.Workbook();b.remove(b.active)
    headers=['No.','SAP번호','PC Name','S/N','Type','Model','Location','User KOR','Lan Connector','소모품 지급','User ENG','AD Account','시작일','만료일','사용기간','잔여개월','Remark']
    for g,name in enumerate(SHEETS):
        s=b.create_sheet(name);h=list(headers)
        if name=='Plant Desktop':h[7]='L. Detail';h[8]='User'
        if name=='창고(SAP자산)':h[9]='Check List'
        for c,v in enumerate(h,2):s.cell(3,c,v)
        for n in range(4):
            i=g*4+n+1;serial=f'DEMO-SN-{i:04d}'
            values=[n+1,f'DEMO-SAP-{i:04d}',f'DEMO-PC-{i:04d}',serial,'Laptop' if i%2 else 'Desktop','Demo Model', ['Seoul','Dan','울산','IT'][n],f'Sample User {i:02d}','Y','Sample item',f'Sample User {i:02d}',f'demo.account{i:02d}',date(2025,11,17),BASE+timedelta(days=[-5,20,50,80][n]),12,None,'Fictional development record']
            if name=='Plant Desktop':values[7]=f'Demo line {n+1}';values[8]=f'Sample User {i:02d}'
            if i in (1,5):values[3]='DEMO-DUPLICATE'
            if i==9:values[3]=None
            if i==10:values[3]='ＤＥＭＯ-００１０'
            if i==14:values[13]=BASE-timedelta(days=5)
            if i==16:values[13]=BASE+timedelta(days=120)
            if i==13:values[12]='미취득';values[13]='#VALUE!';values[4]=None
            for c,v in enumerate(values,2):
                s.cell(n+4,c,v)
                if isinstance(v,date):s.cell(n+4,c).number_format='yyyy-mm-dd'
    b.save(path)
def main():
    p=ROOT/'sample/ITAssets.sample.xlsx';create(p);result=convert(p)
    for k,v in result.items():(ROOT/'sample'/f'{k}.sample.json').write_text(json.dumps(v,ensure_ascii=False,indent=2))
    rows=result['assets_ready'];columns=[x for x in rows[0] if x!='LegacyMetadata']
    with (ROOT/'sample/ITAssets.sample.csv').open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fieldnames=columns,extrasaction='ignore');w.writeheader();w.writerows(rows)
    schema=json.loads((ROOT/'schema/sharepoint-lists.json').read_text())
    keys=sorted({r['LocationKey'] for r in rows}|{'Unknown'})
    (ROOT/'sample/ITLocations.sample.json').write_text(json.dumps([{'Title':'전체 위치','LocationKey':'ALL','SortOrder':0,'SelectableForAsset':False}]+[{'Title':k,'LocationKey':k,'SortOrder':i+1,'SelectableForAsset':True} for i,k in enumerate(keys)],ensure_ascii=False,indent=2))
    from build_sample_views import build
    build()
    print(result['summary'])
if __name__=='__main__':main()
