"""Excel-backed asset store. Never edit the original before validation and backup."""
from pathlib import Path
from datetime import date, datetime
from calendar import monthrange
from copy import copy
import hashlib, os, tempfile, shutil
import openpyxl
from openpyxl.workbook.properties import CalcProperties

SHEETS = ['사무직 List', 'Plant Desktop', '공용 PC', '창고(SAP자산)', '폐기완료']
ERRORS = {'#VALUE!', '#REF!', '#N/A', '#DIV/0!', '#NAME?', '#NUM!', '#NULL!'}
class ConflictError(Exception): pass

def digest(path):
    with open(path, 'rb') as f:
        return hashlib.file_digest(f, 'sha256').hexdigest()

def as_date(value):
    if isinstance(value, datetime): return value.date()
    if isinstance(value, date): return value
    try: return date.fromisoformat(str(value).strip())
    except (ValueError, TypeError): return None

def add_months(day, months):
    m = day.year * 12 + day.month - 1 + months
    y, m = divmod(m, 12)
    return date(y, m + 1, min(day.day, monthrange(y, m + 1)[1]))

def display(value):
    if value is None: return ''
    if isinstance(value, (datetime, date)): return value.strftime('%Y-%m-%d')
    return str(value)

class Store:
    def __init__(self, path):
        self.path = Path(path).resolve()
        if self.path.suffix.lower() != '.xlsx': raise ValueError('xlsx 파일만 지원합니다.')
        before = digest(self.path)
        self.book = openpyxl.load_workbook(self.path)
        self.cache = openpyxl.load_workbook(self.path, data_only=True)
        if digest(self.path) != before: raise ConflictError('읽는 동안 파일이 변경됐습니다. 다시 불러오세요.')
        self.signature = before
        self.sheets = [s for s in SHEETS if s in self.book.sheetnames]
        if not self.sheets: raise ValueError('지원되는 자산 시트를 찾지 못했습니다.')
        for name in self.sheets:
            if self.book[name].cell(3, 5).value != 'S/N':
                raise ValueError(f'{name}: 3행의 열 구성이 원본과 다릅니다.')
        self.pending = []

    def headers(self, sheet):
        return {c: str(self.book[sheet].cell(3,c).value) for c in range(2,19) if self.book[sheet].cell(3,c).value is not None}

    def rows(self):
        result = []
        for name in self.sheets:
            s = self.book[name]
            for r in range(4, s.max_row + 1):
                if not any(s.cell(r,c).value is not None and s.cell(r,c).data_type != 'f' for c in (3,4,5,6,7,8,9)):
                    continue
                vals = {}
                for c in self.headers(name):
                    cell = s.cell(r,c)
                    vals[c] = self.cache[name].cell(r,c).value if cell.data_type == 'f' else cell.value
                result.append({'sheet':name, 'row':r, 'values':vals})
        return result

    def expiry(self, item):
        vals = item['values']
        end = as_date(vals.get(15))
        if end is None:
            start = as_date(vals.get(14))
            try:
                months = int(vals.get(16))
                if start and months > 0: end = add_months(start, months)
            except (ValueError, TypeError, OverflowError): pass
        return end

    def status(self, item):
        if item['sheet'] == '폐기완료': return '폐기완료'
        end = self.expiry(item)
        if end is None: return '날짜 미등록'
        days = (end - date.today()).days
        if days < 0: return '만료'
        if days <= 30: return '30일 이내'
        if days <= 60: return '60일 이내'
        if days <= 90: return '90일 이내'
        return '정상'

    def apply(self, sheet, row, fields):
        s = self.book[sheet]
        adding = row is None
        if adding:
            occupied = [v['row'] for v in self.rows() if v['sheet'] == sheet]
            row = max(occupied, default=3) + 1
        # Validation is completed before changing any cell.
        sn = str(fields.get(5) or '').strip()
        if not sn: raise ValueError('S/N은 필수입니다.')
        fields = dict(fields)
        fields[5] = sn
        for item in self.rows():
            if (item['sheet'],item['row']) != (sheet,row) and str(item['values'].get(5) or '').strip().casefold() == sn.casefold():
                raise ValueError(f"동일한 S/N이 {item['sheet']} 시트 {item['row']}행에 있습니다.")
        if adding:
            for c in range(2,19):
                previous = s.cell(max(4,row-1),c)
                cell = s.cell(row,c)
                cell._style = copy(previous._style)
                cell.number_format = previous.number_format
            numbers = [v['values'].get(2) for v in self.rows() if v['sheet']==sheet]
            s.cell(row,2,max([int(n) for n in numbers if isinstance(n,(int,float))]+[0])+1)
        changed = []
        for c, value in fields.items():
            if c not in self.headers(sheet) or c in (2,17): continue
            cell = s.cell(row,c)
            # Existing formulas are deliberately read-only in the editor.
            if cell.data_type == 'f': continue
            if cell.value != value:
                cell.value = value
                changed.append(str(c))
        if adding:
            from openpyxl.utils.cell import range_boundaries, get_column_letter
            for table in s.tables.values():
                a,b,c,d = range_boundaries(table.ref)
                if b <= 3 and a <= 5 <= c and row > d:
                    table.ref = f'{get_column_letter(a)}{b}:{get_column_letter(c)}{row}'
                    if table.autoFilter: table.autoFilter.ref = table.ref
        if changed or adding: self.pending.append(('등록' if adding else '수정',sheet,row))

    def delete(self, sheet, row):
        # Clear the record instead of shifting rows and breaking cross-sheet formulas.
        s = self.book[sheet]
        for c in range(2,19): s.cell(row,c).value = None
        self.pending.append(('삭제',sheet,row))

    def save(self):
        if not self.pending: return None
        if digest(self.path) != self.signature:
            raise ConflictError('파일이 다른 프로그램 또는 사용자에 의해 변경됐습니다. 저장하지 않았습니다. 변경 내용을 기록한 후 다시 불러오세요.')
        # A local lock coordinates copies of this app on this PC, not remote OneDrive clients.
        lock = self.path.with_name(self.path.name + '.asset-manager.lock')
        excel_lock = self.path.with_name('~$' + self.path.name)
        if excel_lock.exists(): raise ConflictError('엑셀에서 파일을 열어둔 것으로 보입니다. 엑셀을 닫은 후 저장하세요.')
        try: fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        except FileExistsError: raise ConflictError('다른 저장 작업이 진행 중입니다. 잠시 후 다시 시도하세요. 계속되면 안내서를 확인하세요.')
        temp = None
        try:
            os.close(fd)
            if digest(self.path) != self.signature: raise ConflictError('원본이 변경됐습니다. 다시 불러오세요.')
            self.book.calculation = CalcProperties(calcId=0,fullCalcOnLoad=True,forceFullCalc=True)
            fd, temp = tempfile.mkstemp(suffix='.xlsx',dir=self.path.parent)
            os.close(fd)
            self.book.save(temp)
            check = openpyxl.load_workbook(temp,read_only=True)
            check.close()
            if digest(self.path) != self.signature: raise ConflictError('저장 준비 중 원본이 변경됐습니다. 저장을 중단했습니다.')
            folder = self.path.parent / 'IT자산_백업'
            folder.mkdir(exist_ok=True)
            backup = folder / f'{self.path.stem}_{datetime.now():%Y%m%d_%H%M%S_%f}.xlsx'
            shutil.copy2(self.path,backup)
            if digest(backup) != self.signature or digest(self.path) != self.signature:
                raise ConflictError('백업 중 원본이 변경됐습니다. 저장을 중단했습니다.')
            os.replace(temp,self.path)
            temp = None
            self.signature = digest(self.path)
            self.pending.clear()
            return backup
        finally:
            if temp and os.path.exists(temp): os.unlink(temp)
            lock.unlink(missing_ok=True)

    def relocate(self, sheet, row, destination):
        """Move a record without shifting source rows. Roll back on any failure."""
        if destination == sheet: return
        if destination not in self.sheets: raise ValueError('이동할 시트가 없습니다.')
        from copy import deepcopy
        from openpyxl.formula.translate import Translator
        old_book = deepcopy(self.book)
        old_cache = deepcopy(self.cache)
        old_pending = list(self.pending)
        try:
            item = next((x for x in self.rows() if x['sheet']==sheet and x['row']==row),None)
            if not item: raise ValueError('이동할 자산을 찾지 못했습니다.')
            source = self.book[sheet]
            values = {}
            formulas = {}
            extra = []
            target_headers = self.headers(destination)
            def key(label):
                return '사용자' if label in ('User','User KOR') else label
            by_name = {key(v):c for c,v in target_headers.items()}
            for col,label in self.headers(sheet).items():
                if col in (2,17): continue
                value = source.cell(row,col).value
                dest_col = by_name.get(key(label))
                if dest_col:
                    if source.cell(row,col).data_type == 'f':
                        formulas[dest_col] = (source.cell(row,col).coordinate,value)
                        values[dest_col] = item['values'].get(col)
                    else: values[dest_col] = value
                elif value is not None:
                    extra.append(f'{label}: {display(item["values"].get(col))}')
            if extra: values[18] = '\n'.join([display(values.get(18))]+extra).strip()
            # Clear first so the duplicate validator doesn't reject the source S/N.
            for col in range(2,19): source.cell(row,col).value = None
            occupied = [x['row'] for x in self.rows() if x['sheet']==destination]
            newrow = max(occupied,default=3)+1
            # The template can contain formulas below the last populated record.
            for col in range(2,19):
                self.book[destination].cell(newrow,col).value = None
                self.cache[destination].cell(newrow,col).value = None
            self.apply(destination,None,values)
            for col,(origin,value) in formulas.items():
                target = self.book[destination].cell(newrow,col)
                target.value = Translator(value,origin=origin).translate_formula(target.coordinate)
                self.cache[destination].cell(newrow,col).value = values.get(col)
            self.pending = old_pending + [('이동: '+sheet+' → '+destination,destination,newrow)]
        except Exception:
            self.book,self.cache,self.pending = old_book,old_cache,old_pending
            raise
