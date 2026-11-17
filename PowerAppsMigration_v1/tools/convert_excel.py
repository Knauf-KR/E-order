"""Local-only staging converter. No SharePoint calls, uploads, or source writes."""
import argparse, json, re, hashlib, uuid, unicodedata, calendar
from pathlib import Path
from datetime import date,datetime
from collections import Counter
import openpyxl
ROOT=Path(__file__).resolve().parents[1]
SHEETS={'사무직 List':('Office','InUse'),'Plant Desktop':('Plant','InUse'),'공용 PC':('Shared','InUse'),'창고(SAP자산)':('Unassigned','Stock'),'폐기완료':('Unassigned','Retired')}
ERRORS={'#REF!','#VALUE!','#N/A','#DIV/0!','#NAME?','#NUM!','#NULL!'}
def text(v):
    if v is None:return ''
    if isinstance(v,(datetime,date)):return v.strftime('%Y-%m-%d')
    return str(v)
def serial(v):
    # Canonical write flow only accepts ASCII keys. Full-width conversions need review.
    s=unicodedata.normalize('NFKC',text(v))
    return re.sub(r'\s+','',s).upper()
def day(v):
    if isinstance(v,datetime):return v.date()
    if isinstance(v,date):return v
    try:return date.fromisoformat(str(v).strip())
    except (ValueError,TypeError):return None
def months_after(d,n):
    y,m=divmod(d.year*12+d.month-1+n,12)
    return date(y,m+1,min(d.day,calendar.monthrange(y,m+1)[1]))
def location(v):
    s=text(v).strip();aliases={'dan':'Dangjin','dangjin':'Dangjin','당진':'Dangjin','uls':'Ulsan','ulsan':'Ulsan','울산':'Ulsan','yeo':'Yeosu','yosu':'Yeosu','yeosu':'Yeosu','여수':'Yeosu','seoul':'Seoul','서울':'Seoul'}
    return aliases.get(s.casefold(),s or 'Unknown')
def convert(path):
    path=Path(path);fingerprint=hashlib.sha256(path.read_bytes()).hexdigest()
    formulas=openpyxl.load_workbook(path,read_only=True,data_only=False);cached=openpyxl.load_workbook(path,read_only=True,data_only=True)
    proposed=[];staging=[]
    try:
        for name,(group,state) in SHEETS.items():
            if name not in formulas.sheetnames:continue
            f,c=formulas[name],cached[name]
            if f.cell(3,5).value!='S/N':raise ValueError(f'{name}: E3 is not S/N; stop instead of guessing columns')
            if (f.max_column or 18)>256:raise ValueError(f'{name}: excessive column range; review before mapping')
            if (f.max_column or 18)>18:
                for extra in f.iter_rows(min_row=3,min_col=19,max_col=f.max_column,values_only=True):
                    if any(v is not None for v in extra):raise ValueError(f'{name}: unmapped values beyond R; stop for review')

            for r,(fc,cv) in enumerate(zip(f.iter_rows(min_row=4,max_col=18),c.iter_rows(min_row=4,max_col=18,values_only=True)),4):
                if not any(fc[i-1].value is not None and fc[i-1].data_type!='f' for i in (3,4,5,6,7,8,9)):continue
                values={i:(cv[i-1] if fc[i-1].data_type=='f' else fc[i-1].value) for i in range(2,19)}
                raw={str(i):{'value':text(values[i]),'formula':fc[i-1].value if fc[i-1].data_type=='f' else None} for i in range(2,19)}
                issues=[]
                if any(v in ERRORS for v in map(text,values.values())):issues.append('LegacyFormulaError')
                def clean(i):return '' if text(values[i]) in ERRORS else text(values[i])
                sn=serial(values[5]);rawtype=clean(6);dtype={'laptop':'Laptop','desktop':'Desktop','other':'Other'}.get(rawtype.casefold(),'Unknown')
                if dtype=='Unknown':issues.append('DeviceTypeReview')
                if not clean(7):issues.append('MissingModel')
                if not clean(8) and state!='Retired':issues.append('MissingLocation')
                if state=='InUse' and group=='Office' and not clean(9):issues.append('MissingUser')
                start=day(values[14]);expiry=day(values[15]);basis='Explicit' if expiry else 'Unknown'
                try:n=int(values[16]);n=n if 1<=n<=1200 else None
                except (ValueError,TypeError):n=None
                if not expiry and start and n:
                    try:expiry=months_after(start,n);basis='Derived'
                    except (ValueError,OverflowError):issues.append('InvalidDateRange')
                if not expiry and state!='Retired':issues.append('MissingExpiry')
                if start and expiry and expiry<start:issues.append('ExpiryBeforeStart')
                if not sn or not re.fullmatch(r'[A-Z0-9-]{1,255}',sn):issues.append('InvalidSerial')
                if sn != re.sub(r'\s+','',text(values[5])).upper():issues.append('UnicodeSerialReview')
                key=str(uuid.uuid5(uuid.NAMESPACE_URL,f'it-assets/{fingerprint}/{name}/{r}'))
                item={'AssetKey':key,'SerialNumber':clean(5),'SerialKey':sn,'SAPAssetNumber':clean(3),'PCName':clean(4),'Model':clean(7),'AssignedUserKOR':clean(10) if name=='Plant Desktop' else clean(9),'AssignedUserENG':clean(12),'ADAccount':clean(13),'LocationKey':location(values[8]),'LocationRaw':clean(8),'LocationDetail':clean(9) if name=='Plant Desktop' else '', 'DeviceTypeRaw':rawtype,'LanConnectorRaw':'' if name=='Plant Desktop' else clean(10),'ConsumablesRaw':'' if name=='창고(SAP자산)' else clean(11),'ChecklistRaw':clean(11) if name=='창고(SAP자산)' else '', 'LegacyNo':clean(2),'SourceSheet':name,'LegacyStartText':text(values[14]),'LegacyExpiryText':text(values[15]),'LegacyRemainingText':text(values[17]),'AssetGroup':group,'LifecycleState':state,'DeviceType':dtype,'AcquisitionState':'Unacquired' if clean(14)=='미취득' else 'Acquired' if start else 'Unknown','ExpirySource':basis,'StartDate':text(start) or None,'ExpiryDate':text(expiry) or None,'RetiredOn':None,'UsageMonths':n,'HasExpiry':bool(expiry),'HasDataIssues':bool(issues),'IsDeleted':False,'SourceRow':r,'Remarks':clean(18),'IssueCodes':'|'.join(issues),'LegacyMetadata':json.dumps(raw,ensure_ascii=False)}
                proposed.append(item)
        count=Counter(i['SerialKey'] for i in proposed if i['SerialKey'])
        ready=[]
        for i in proposed:
            issues=i['IssueCodes'].split('|') if i['IssueCodes'] else []
            if count[i['SerialKey']]>1:issues.append('DuplicateSerial')
            i['IssueCodes']='|'.join(issues);i['HasDataIssues']=bool(issues)
            blocked=any(x in issues for x in ['DuplicateSerial','InvalidSerial','UnicodeSerialReview'])
            staging.append({'SourceKey':i['AssetKey'],'SerialKey':i['SerialKey'],'ReviewState':'NeedsSerialReview' if blocked else 'Ready','SourceSheet':i['SourceSheet'],'SourceRow':i['SourceRow'],'IssueCodes':i['IssueCodes'],'ProposedAsset':json.dumps(i,ensure_ascii=False),'LegacyMetadata':i['LegacyMetadata']})
            if not blocked:ready.append(i)
        assert hashlib.sha256(path.read_bytes()).hexdigest()==fingerprint,'Source changed during conversion'
        return {'staging':staging,'assets_ready':ready,'summary':{'total':len(staging),'ready':len(ready),'serial_review':len(staging)-len(ready),'duplicate_groups':sum(v>1 for v in count.values()),'invariant':'ready + serial_review == total; all original rows retained in staging'}}
    finally:formulas.close();cached.close()
def main():
    p=argparse.ArgumentParser();p.add_argument('--input',required=True,type=Path);p.add_argument('--output',required=True,type=Path);p.add_argument('--sample',action='store_true');a=p.parse_args()
    out=a.output.resolve()
    if out.is_relative_to(ROOT) and not a.sample:raise SystemExit('Real conversion output must be outside the release folder. Do not publish real rows.')
    out.mkdir(parents=True,exist_ok=True)
    result=convert(a.input)
    for key,value in result.items():(out/f'{key}.json').write_text(json.dumps(value,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(result['summary'],ensure_ascii=False))
if __name__=='__main__':main()
