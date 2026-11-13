"""Regression tests using only generated fictional data. Run: python -m unittest -v"""
import tempfile, unittest
from pathlib import Path
from datetime import date, timedelta
import openpyxl
from create_demo import create_demo
from storage import Store, ConflictError, add_months

class AssetTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.path=Path(self.temp.name)/'test.xlsx'
        create_demo(self.path)
        self.store=Store(self.path)
    def tearDown(self):self.temp.cleanup()
    def edit(self):self.store.apply('사무직 List',4,{5:'DEMO-SN-1',18:'테스트 변경'})
    def test_backup_and_explicit_save(self):
        before=self.path.read_bytes();self.edit();self.assertEqual(before,self.path.read_bytes())
        backup=self.store.save();self.assertEqual(before,backup.read_bytes())
        self.assertEqual(Store(self.path).rows()[0]['values'][18],'테스트 변경')
    def test_external_edit_not_overwritten(self):
        self.edit();b=openpyxl.load_workbook(self.path);b['사무직 List']['R4']='외부 변경';b.save(self.path)
        before=self.path.read_bytes()
        with self.assertRaises(ConflictError):self.store.save()
        self.assertEqual(before,self.path.read_bytes());self.assertTrue(self.store.pending)
    def test_missing_and_duplicate_serial(self):
        for sn in [None,'','   ','demo-sn-1']:
            with self.assertRaises(ValueError):self.store.apply('공용 PC',None,{5:sn,6:'Laptop'})
        self.assertEqual(len(self.store.rows()),5);self.assertFalse(self.store.pending)
    def test_excel_lock(self):
        self.edit();self.path.with_name('~$test.xlsx').touch()
        with self.assertRaises(ConflictError):self.store.save()
    def test_move_maps_user_and_preserves_extra_columns(self):
        self.store.relocate('Plant Desktop',4,'공용 PC')
        records=self.store.rows();self.assertEqual(len(records),5)
        moved=next(i for i in records if i['values'][5]=='DEMO-SN-2')
        self.assertEqual(moved['sheet'],'공용 PC');self.assertEqual(moved['values'][9],'가상 사용자 2')
        self.assertIn('L. Detail: 체험 현장',moved['values'][18])
        self.assertIsNone(self.store.book['Plant Desktop']['E4'].value)
        self.store.save();self.assertEqual(len(Store(self.path).rows()),5)
    def test_move_translates_formulas(self):
        self.store.book['Plant Desktop']['O4']='=EDATE(N4,P4)'
        self.store.relocate('Plant Desktop',4,'창고(SAP자산)')
        self.assertEqual(self.store.book['창고(SAP자산)']['O5'].value,'=EDATE(N5,P5)')
    def test_failed_move_rolls_back(self):
        self.store.book['공용 PC']['E4']='DEMO-SN-2'
        before=[(i['sheet'],i['row'],dict(i['values'])) for i in self.store.rows()]
        with self.assertRaises(ValueError):self.store.relocate('Plant Desktop',4,'공용 PC')
        self.assertEqual(before,[(i['sheet'],i['row'],dict(i['values'])) for i in self.store.rows()])
        self.assertFalse(self.store.pending)
    def test_delete_does_not_shift_other_rows(self):
        cell=self.store.book['공용 PC']['E4'].value;self.store.delete('사무직 List',4)
        self.assertEqual(self.store.book['공용 PC']['E4'].value,cell)
        self.store.save();self.assertEqual(len(Store(self.path).rows()),4)
    def test_expiry_boundaries(self):
        for days,expected in [(-1,'만료'),(0,'30일 이내'),(30,'30일 이내'),(31,'60일 이내'),(60,'60일 이내'),(61,'90일 이내'),(90,'90일 이내'),(91,'정상')]:
            item={'sheet':'사무직 List','values':{15:date.today()+timedelta(days=days)}}
            self.assertEqual(self.store.status(item),expected)
        self.assertEqual(add_months(date(2024,2,29),12),date(2025,2,28))
    def test_formula_preserved_on_ordinary_edit(self):
        self.store.book['사무직 List']['Q4']='=1+2';self.edit();self.store.save()
        b=openpyxl.load_workbook(self.path);self.assertEqual(b['사무직 List']['Q4'].value,'=1+2');b.close()

if __name__=='__main__':unittest.main()
