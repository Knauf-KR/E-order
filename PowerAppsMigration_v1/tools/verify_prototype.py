from playwright.sync_api import sync_playwright
from pathlib import Path
import argparse
parser=argparse.ArgumentParser();parser.add_argument('--url',default='http://127.0.0.1:8877/prototype/index.html');parser.add_argument('--browser-executable');args=parser.parse_args()
root=Path(__file__).resolve().parents[1]
with sync_playwright() as p:
 browser=p.chromium.launch(executable_path=args.browser_executable,headless=True,args=['--no-sandbox'])
 page=browser.new_page(viewport={'width':1440,'height':1000});errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
 page.goto(args.url)
 assert page.locator('#rows tr').count()==16
 page.locator('#q').fill('0002');assert page.locator('#rows tr').count()==0
 page.locator('#searchMode').select_option('precise');assert page.locator('#rows tr').count()==1
 page.locator('#q').fill('DEMO 0002');assert page.locator('#rows tr').count()==1
 page.locator('#rows tr').first.click();assert page.locator('#overlay').is_visible()
 assert page.locator('input[name="PCName"]').get_attribute('readonly') is not None
 page.keyboard.press('Escape');assert not page.locator('#overlay').is_visible()
 page.locator('#nav button[data-page="office"]').click();assert page.locator('#rows tr').count()==3
 page.locator('#rows tr').first.click();page.locator('#edit').click()
 page.locator('input[name="PCName"]').fill('DEMO-EDITED-UI');page.locator('#save').click()
 assert page.get_by_text('DEMO-EDITED-UI',exact=True).is_visible()
 page.locator('#nav button[data-page="quality"]').click();assert '4' in page.locator('#review').inner_text()
 page.locator('#nav button[data-page="all"]').click();# No screenshot file is written by this verification script.
 page.set_viewport_size({'width':390,'height':844});page.locator('#nav button[data-page="shared"]').click()
 assert page.locator('#rows tr').count()==2
 assert not errors,errors
 browser.close()
print('PASS: browser mockup 16 records; prefix versus all-token substring; sheet pages; readonly modal; edit simulation; review notice; mobile layout; no JS errors')
