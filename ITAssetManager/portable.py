"""Locate the shared workbook relative to the launcher, never the working directory."""
import sys
from pathlib import Path

WORKBOOK_NAME = 'IT_자산리스트.xlsx'

def asset_directory(explicit=None, *, script_file=None, executable=None, frozen=None):
    if explicit is not None:
        return Path(explicit).expanduser().resolve()
    if frozen is None:
        frozen = getattr(sys, 'frozen', False)
    if frozen:
        return Path(executable or sys.executable).resolve().parent
    base = Path(script_file or __file__).resolve().parent
    # Source package in a folder beside the workbook; also support a flat layout.
    if base.name == 'ITAssetManager' and not (base / WORKBOOK_NAME).is_file():
        return base.parent
    return base

def workbook_path(directory):
    # Do not guess among other financial/SAP workbooks in the shared folder.
    return Path(directory).resolve() / WORKBOOK_NAME
