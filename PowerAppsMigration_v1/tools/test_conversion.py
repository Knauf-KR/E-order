import unittest,tempfile,hashlib,json,subprocess,sys
from pathlib import Path
from datetime import date
import openpyxl
from make_samples import create
from convert_excel import convert,months_after,serial,ROOT

class ConversionTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.path=Path(self.tmp.name)/'fictional.xlsx';create(self.path)
    def tearDown(self):self.tmp.cleanup()
    def test_conservation_duplicate_quarantine_and_source_unchanged(self):
        before=self.path.read_bytes();r=convert(self.path)
        self.assertEqual(r['summary']['total'],20);self.assertEqual(len(r['staging']),20);self.assertEqual(len(r['assets_ready']),16)
        self.assertEqual(sum(x['ReviewState']=='NeedsSerialReview' for x in r['staging']),4)
        self.assertEqual(before,self.path.read_bytes())
    def test_plant_user_and_location_detail_are_separate(self):
        r=convert(self.path);x=next(x for x in r['assets_ready'] if x['PCName']=='DEMO-PC-0006')
        self.assertEqual(x['AssignedUserKOR'],'Sample User 06');self.assertEqual(x['LocationDetail'],'Demo line 2');self.assertEqual(x['LanConnectorRaw'],'')
    def test_same_source_is_idempotent(self):
        a=convert(self.path);b=convert(self.path)
        self.assertEqual([x['SourceKey'] for x in a['staging']],[x['SourceKey'] for x in b['staging']])
    def test_unacquired_error_and_original_values_remain(self):
        r=convert(self.path);x=next(x for x in r['assets_ready'] if x['PCName']=='DEMO-PC-0013')
        self.assertIsNone(x['StartDate']);self.assertIsNone(x['ExpiryDate']);self.assertEqual(x['AcquisitionState'],'Unacquired')
        self.assertEqual(json.loads(x['LegacyMetadata'])['15']['value'],'#VALUE!')
    def test_normalization_does_not_confuse_zero(self):
        self.assertEqual(serial(' demo\u00a0-sn-01 '),'DEMO-SN-01');self.assertNotEqual(serial('DEMO-O1'),serial('DEMO-01'))
    def test_end_of_month(self):
        self.assertEqual(months_after(date(2025,1,31),1),date(2025,2,28));self.assertEqual(months_after(date(2024,2,29),12),date(2025,2,28))
    def test_unknown_type_not_silently_corrected(self):
        b=openpyxl.load_workbook(self.path);b['사무직 List']['F5']='Dekstop';b.save(self.path);b.close()
        x=next(x for x in convert(self.path)['assets_ready'] if x['PCName']=='DEMO-PC-0002')
        self.assertEqual(x['DeviceTypeRaw'],'Dekstop');self.assertEqual(x['DeviceType'],'Unknown');self.assertIn('DeviceTypeReview',x['IssueCodes'])
    def test_unmapped_data_is_not_silently_dropped(self):
        b=openpyxl.load_workbook(self.path);b['사무직 List']['S4']='DEMO EXTRA';b.save(self.path);b.close()
        with self.assertRaisesRegex(ValueError,'beyond R'):convert(self.path)
    def test_real_output_guard(self):
        p=subprocess.run([sys.executable,str(ROOT/'tools/convert_excel.py'),'--input',str(self.path),'--output',str(ROOT/'forbidden-test-output')],capture_output=True,text=True)
        self.assertNotEqual(p.returncode,0);self.assertFalse((ROOT/'forbidden-test-output').exists())

if __name__=='__main__':unittest.main()
