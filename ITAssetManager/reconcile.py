"""Read-only SAP reconciliation; no network calls and no source workbook writes."""
import re, unicodedata
from pathlib import Path
from collections import defaultdict
import openpyxl
from storage import display, digest

STATUSES=['일치','IT 목록에 없음','폐기목록에만 존재','SAP번호 불일치','중복 S/N','S/N 확인 필요','종류 확인 필요','SAP에서 미확인','대상외']

def serial_key(value):
    return re.sub(r'\s+','',unicodedata.normalize('NFKC',display(value))).upper()

def asset_key(value):
    if isinstance(value,float) and value.is_integer():value=int(value)
    return display(value).strip()

def pc_type(value):
    text=display(value).casefold()
    if re.search(r'desktop|데스크|elitedesk|prodesk|elitemini|elite mini|optiplex|thinkcentre',text):return 'Desktop'
    if re.search(r'laptop|notebook|노트북|elitebook|probook|zbook|thinkpad|latitude|\beb\d|elite\s*x2',text):return 'Laptop'
    return ''

def extract_serials(description,explicit=None):
    if explicit is not None and display(explicit).strip():
        tokens=re.split(r'[,;\n]+',display(explicit))
        return list(dict.fromkeys(serial_key(x) for x in tokens if serial_key(x))), 'S/N 열'
    text=unicodedata.normalize('NFKC',display(description)).upper()
    known=re.findall(r'(?<![A-Z0-9])(?:5C[GD][A-Z0-9]{7}|8CC[A-Z0-9]{7}|CND[A-Z0-9]{7})(?![A-Z0-9])',text)
    labelled=re.findall(r'(?:S\s*/?\s*N|SERIAL(?:\s*NUMBER)?|시리얼)\s*[:=#-]?\s*([A-Z0-9][A-Z0-9-]{5,29})',text)
    suffix=[]
    if '/' in text:
        for token in re.split(r'[,;\s]+',text.rsplit('/',1)[1].strip()):
            token=token.strip('()[]{}.')
            if re.fullmatch(r'[A-Z0-9-]{7,25}',token) and re.search('[A-Z]',token) and re.search('[0-9]',token):suffix.append(token)
    return list(dict.fromkeys(serial_key(x) for x in known+labelled+suffix)), '자산 설명에서 추출'

ALIASES={
 'asset':['asset','자산번호','sap번호'],
 'description':['assetdescription','자산내역','자산설명','description'],
 'sub':['subnumber','하위번호'],
 'serial':['sn','serialnumber','serial','시리얼번호'],
}
def header_key(x):return re.sub(r'[^a-z0-9가-힣]','',display(x).casefold())

class SapBook:
    def __init__(self,path):
        self.path=Path(path).resolve()
        if self.path.suffix.lower()!='.xlsx':raise ValueError('SAP 파일은 xlsx 형식으로 선택하세요.')
        before=digest(self.path);self.sheets={};self.headers={}
        book=openpyxl.load_workbook(self.path,read_only=True,data_only=True)
        try:
            for sheet in book:
                header=None
                # SAP formatting can extend the worksheet to XFD. Never expand that width.
                for rownum,row in enumerate(sheet.iter_rows(max_row=min(30,sheet.max_row or 30),max_col=min(256,sheet.max_column or 256),values_only=True),1):
                    normalized={header_key(v):i for i,v in enumerate(row) if v is not None}
                    found={key:next((normalized[x] for x in names if x in normalized),None) for key,names in ALIASES.items()}
                    if found['asset'] is not None and found['description'] is not None:
                        header=(rownum,found);break
                if not header:continue
                self.headers[sheet.title]=header
                rownum,cols=header;records=[];maxcol=max(v for v in cols.values() if v is not None)+1
                for r,row in enumerate(sheet.iter_rows(min_row=rownum+1,max_col=maxcol,values_only=True),rownum+1):
                    def val(key):return row[cols[key]] if cols.get(key) is not None else None
                    asset=asset_key(val('asset'));desc=display(val('description')).strip()
                    if not asset or not desc:continue
                    serials,method=extract_serials(desc,val('serial'))
                    kind=pc_type(desc)
                    if not kind and serials:kind='PC 후보'
                    records.append({'asset':asset,'sub':asset_key(val('sub')),'description':desc,'serials':serials,'method':method,'type':kind,'sheet':sheet.title,'row':r})
                self.sheets[sheet.title]=records
        finally:book.close()
        if digest(self.path)!=before:raise ValueError('SAP 파일을 읽는 동안 변경됐습니다. 다시 선택하세요.')
        self.signature=before
        if not self.sheets:raise ValueError('Asset / Asset description 열이 있는 SAP 시트를 찾지 못했습니다. 요약·폐기 시트는 대조 대상이 아닙니다.')

def compare(sap_rows,it_rows):
    index=defaultdict(list)
    for item in it_rows:
        sn=serial_key(item['values'].get(5))
        if sn:index[sn].append(item)
    sap_index=defaultdict(list)
    for sap in sap_rows:
        if sap['type']:
            for sn in sap['serials']:sap_index[sn].append(sap)
    results=[]
    for sap in sap_rows:
        if not sap['type']:
            results.append(_result(sap,'','대상외',[],'PC로 분류되지 않은 자산입니다. 분류를 검토할 수 있도록 남겨둡니다.'));continue
        if not sap['serials']:
            results.append(_result(sap,'','S/N 확인 필요',[],'설명에서 S/N을 확인할 수 없습니다. 묶음 자산·구형 장비를 누락으로 판정하지 않습니다.'));continue
        for sn in sap['serials']:
            matches=index.get(sn,[]);notes=[]
            if len(matches)>1 or len(sap_index[sn])>1:
                status='중복 S/N';notes.append(f'선택 SAP 시트 {len(sap_index[sn])}행 / IT 목록 {len(matches)}행. 개별 확인이 필요합니다.')
            elif not matches and sap['type']=='PC 후보':
                status='종류 확인 필요';notes.append('추출한 S/N은 있지만 PC 모델을 확인하지 못했습니다. 장비 분류부터 확인하세요.')
            elif not matches:status='IT 목록에 없음'
            elif matches[0]['sheet']=='폐기완료':status='폐기목록에만 존재'
            elif not pc_type(matches[0]['values'].get(6)):
                status='종류 확인 필요';notes.append('S/N은 있으나 IT 장비 종류가 Desktop/Laptop으로 확인되지 않습니다.')
            elif asset_key(matches[0]['values'].get(3)) and asset_key(matches[0]['values'].get(3))!=sap['asset']:
                status='SAP번호 불일치';notes.append('S/N은 일치하지만 IT 목록의 SAP번호가 다릅니다.')
            else:status='일치'
            if matches and not matches[0]['values'].get(3):notes.append('IT 목록의 SAP번호는 미등록입니다. S/N 기준으로 대조했습니다.')
            if sap['type']=='PC 후보':notes.append('설명에서 PC 모델명을 확인하지 못했습니다. 장비 종류를 검토하세요.')
            results.append(_result(sap,sn,status,matches,' '.join(notes)))
    for item in it_rows:
        if item['sheet']=='폐기완료' or not (pc_type(item['values'].get(6)) or pc_type(item['values'].get(7))):continue
        sn=serial_key(item['values'].get(5))
        if not sn or sn not in sap_index:
            results.append({'direction':'IT → SAP','status':'SAP에서 미확인','serial':sn,'asset':asset_key(item['values'].get(3)),'description':display(item['values'].get(7)),'type':display(item['values'].get(6)),'sap_source':'','method':'IT S/N 기준','matches':[item],'notes':'선택한 SAP 시트의 추출 가능한 S/N에서 찾지 못했습니다. 기준월 차이·묶음 자산·S/N 미기재 가능성이 있으므로 SAP 미등록으로 단정할 수 없습니다.'})
    return results

def _result(sap,sn,status,matches,notes):
    return {'direction':'SAP → IT','status':status,'serial':sn,'asset':sap['asset'],'description':sap['description'],'type':sap['type'],'sap_source':f"{sap['sheet']} / {sap['row']}행 / 하위번호 {sap['sub']}",'method':sap['method'],'matches':matches,'notes':notes}
