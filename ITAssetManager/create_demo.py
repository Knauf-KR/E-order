"""Create a demo workbook with entirely fictional data, without user assets."""
from datetime import date, timedelta
from pathlib import Path
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill
from storage import SHEETS

def create_demo(path):
    book = Workbook()
    book.remove(book.active)
    headers = ['No.','SAP번호','PC Name','S/N','Type','Model','Location','User KOR','Lan Connector','소모품 지급','User ENG','AD Account','시작일','만료일','사용기간','잔여개월','Remark']
    for index, name in enumerate(SHEETS):
        sheet = book.create_sheet(name)
        sheet_headers=list(headers)
        if name=='Plant Desktop':
            sheet_headers[7]='L. Detail';sheet_headers[8]='User'
        for col, label in enumerate(sheet_headers, 2):
            cell = sheet.cell(3, col, label)
            cell.font = Font(bold=True, color='FFFFFF')
            cell.fill = PatternFill('solid', fgColor='1769AA')
            sheet.column_dimensions[cell.column_letter].width = 20
        end = date.today() + timedelta(days=[-10,20,50,80,200][index])
        values = [1, 'DEMO-'+str(index+1), 'DEMO-PC-'+str(index+1), 'DEMO-SN-'+str(index+1), 'Laptop', 'Demo Laptop', '체험 사업장', '가상 사용자 '+str(index+1), None, None, None, None, date.today()-timedelta(days=365), end, 12, None, '실제 자산 정보가 아닌 가상 체험 데이터입니다.']
        if name=='Plant Desktop':
            values[7]='체험 현장';values[8]='가상 사용자 2'
        if name=='창고(SAP자산)':values[6]=None
        for col, value in enumerate(values, 2):
            sheet.cell(4, col, value)
            if isinstance(value, date): sheet.cell(4, col).number_format='yyyy-mm-dd'
        sheet.freeze_panes='B4'
    book.save(Path(path))

if __name__ == '__main__':
    create_demo(Path(__file__).with_name('체험용_IT_자산리스트.xlsx'))
