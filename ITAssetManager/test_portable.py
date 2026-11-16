import os, tempfile, unittest
from pathlib import Path
from portable import asset_directory, workbook_path, WORKBOOK_NAME

class PortableTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name)/'공유 폴더 with spaces';self.root.mkdir()
    def tearDown(self):self.tmp.cleanup()
    def test_launcher_directory_wins_over_working_directory(self):
        other=Path(self.tmp.name)/'unrelated';other.mkdir();original=Path.cwd()
        try:
            os.chdir(other)
            self.assertEqual(workbook_path(asset_directory(self.root)),self.root/WORKBOOK_NAME)
        finally:os.chdir(original)
    def test_each_user_has_a_different_prefix(self):
        for user in ['user_one','다른 사용자']:
            folder=self.root/user/'OneDrive 공유';folder.mkdir(parents=True)
            self.assertEqual(workbook_path(asset_directory(folder)),folder/WORKBOOK_NAME)
    def test_source_package_beside_workbook(self):
        package=self.root/'ITAssetManager';package.mkdir();(self.root/WORKBOOK_NAME).touch()
        self.assertEqual(asset_directory(script_file=package/'app.py',frozen=False),self.root)
    def test_flat_source_layout(self):
        (self.root/WORKBOOK_NAME).touch()
        self.assertEqual(asset_directory(script_file=self.root/'app.py',frozen=False),self.root)
    def test_future_frozen_executable_uses_its_own_folder(self):
        self.assertEqual(asset_directory(executable=self.root/'AssetManager.exe',frozen=True),self.root)
    def test_no_guessing_among_other_workbooks_or_demo(self):
        for name in ['SAP.xlsx','other.xlsx','체험용_IT_자산리스트.xlsx']:(self.root/name).touch()
        target=workbook_path(self.root)
        self.assertEqual(target.name,WORKBOOK_NAME);self.assertFalse(target.exists())

if __name__=='__main__':unittest.main()
