import unittest,tempfile
from pathlib import Path
import openpyxl
from storage import Store,digest
from reconcile import SapBook,compare,extract_serials,serial_key
from create_demo import create_demo
from sync_policy import SyncPolicy

class SyncTests(unittest.TestCase):
    def test_requires_stable_revision(self):
        p=SyncPolicy();self.assertEqual(p.observe('new','old',False),'waiting');self.assertEqual(p.observe('new','old',False),'reload')
    def test_dialog_or_pending_blocks_reload(self):
        p=SyncPolicy();self.assertEqual(p.observe('new','old',True),'blocked');self.assertEqual(p.observe('new','old',True),'blocked');self.assertEqual(p.observe('new','old',False),'reload')
    def test_changing_revision_restarts_stability(self):
        p=SyncPolicy();p.observe('a','old',False);self.assertEqual(p.observe('b','old',False),'waiting')
    def test_own_save_resets_revision(self):
        p=SyncPolicy();p.observe('a','old',False);self.assertEqual(p.observe('a','a',False),'same')

class SapTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.path=Path(self.tmp.name)/'it.xlsx';create_demo(self.path);self.store=Store(self.path)
    def tearDown(self):self.tmp.cleanup()
    def sap(self,sn,asset='DEMO-1',description='Laptop',row=2):
        return {'asset':asset,'sub':'0','description':description,'serials':[sn] if sn else [],'method':'S/N 열','type':'Laptop','sheet':'K-GAAP','row':row}
    def test_normalization_does_not_confuse_zero_and_letter(self):
        self.assertEqual(serial_key(' 5cg 123\u00a0ABC '),'5CG123ABC');self.assertNotEqual(serial_key('ABC0'),serial_key('ABCO'))
    def test_extract_description_and_no_model_false_positive(self):
        self.assertEqual(extract_serials('HP EB8G1a14 5CG6254YB2\u00a0')[0],['5CG6254YB2'])
        self.assertEqual(extract_serials('HP EliteBook 845 G10 / 5CG4073PQK')[0],['5CG4073PQK'])
        self.assertEqual(extract_serials('Laptop and Desktop Refreshment (30ea)')[0],[])
        self.assertEqual(extract_serials('HP EB8G1a14')[0],[])
    def test_match_missing_retired_and_id_disagreement(self):
        rows=[self.sap('DEMO-SN-1'),self.sap('UNKNOWN1',row=3),self.sap('DEMO-SN-5',row=4),self.sap('DEMO-SN-2',asset='WRONG',row=5)]
        statuses=[r['status'] for r in compare(rows,self.store.rows()) if r['direction']=='SAP → IT']
        self.assertEqual(statuses,['일치','IT 목록에 없음','폐기목록에만 존재','SAP번호 불일치'])
    def test_missing_serial_not_reported_as_missing_asset(self):
        rows=compare([self.sap(None)],self.store.rows());self.assertEqual(rows[0]['status'],'S/N 확인 필요')
        self.assertTrue(any(r['status']=='SAP에서 미확인' for r in rows))
    def test_duplicates_on_both_sides(self):
        rows=[self.sap('DEMO-SN-1'),self.sap('DEMO-SN-1',row=3)]
        self.assertTrue(all(r['status']=='중복 S/N' for r in compare(rows,self.store.rows())[:2]))
        self.store.book['공용 PC']['E4']='DEMO-SN-1'
        self.assertEqual(compare(rows[:1],self.store.rows())[0]['status'],'중복 S/N')
    def test_reader_chooses_one_ledger_and_bounds_huge_dimensions(self):
        p=Path(self.tmp.name)/'sap.xlsx';b=openpyxl.Workbook();b.active.title='Summary'
        for name in ['K-GAAP','IFRS','HGB']:
            s=b.create_sheet(name);s.append(['Asset','Sub-number','Asset description']);s.append(['DEMO-1','0','Laptop / DEMO-SN-1'])
            s.cell(4,16384).number_format='@'
        b.save(p);before=digest(p);sap=SapBook(p)
        self.assertEqual(set(sap.sheets),{'K-GAAP','IFRS','HGB'});self.assertEqual(len(sap.sheets['K-GAAP']),1)
        self.assertEqual(compare(sap.sheets['K-GAAP'],self.store.rows())[0]['status'],'일치');self.assertEqual(before,digest(p))
    def test_non_pc_retained_for_review(self):
        row=self.sap(None,description='Factory land');row['type']=''
        self.assertEqual(compare([row],[])[0]['status'],'대상외')

if __name__=='__main__':unittest.main()
