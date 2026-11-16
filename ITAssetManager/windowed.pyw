"""Windowed entry point; report startup errors even when no console exists."""
import contextlib
import os
from pathlib import Path
import runpy
import traceback


def main():
    folder = Path(os.environ.get('LOCALAPPDATA', Path.home())) / 'KnaufITAssetManager'
    log = folder / 'app-startup.log'
    try:
        folder.mkdir(parents=True, exist_ok=True)
        with log.open('a', encoding='utf-8') as stream:
            with contextlib.redirect_stdout(stream), contextlib.redirect_stderr(stream):
                runpy.run_path(str(Path(__file__).with_name('app.py')), run_name='__main__')
    except Exception as exc:
        try:
            folder.mkdir(parents=True, exist_ok=True)
            with log.open('a', encoding='utf-8') as stream:
                traceback.print_exc(file=stream)
        except OSError:
            pass
        if os.name == 'nt':
            import ctypes
            ctypes.windll.user32.MessageBoxW(None, f'{exc}\n\nError log: {log}', 'Knauf IT Asset Manager', 0x10)
        else:
            raise


if __name__ == '__main__':
    main()
