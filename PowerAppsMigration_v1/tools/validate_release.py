"""Static/local validation. Explicitly does not compile Power Fx or import an app."""
from pathlib import Path
import json,hashlib,argparse,re
ROOT=Path(__file__).resolve().parents[1]
def balanced(source):
    stack=[];pairs={')':'(',']':'[','}':'{'};i=0;quoted=False
    while i<len(source):
        ch=source[i]
        if quoted:
            if ch=='"':
                if i+1<len(source) and source[i+1]=='"':i+=2;continue
                quoted=False
        elif ch=='"':quoted=True
        elif source[i:i+2]=='//':
            end=source.find('\n',i);i=len(source) if end<0 else end;continue
        elif ch in '([{':stack.append(ch)
        elif ch in ')]}':
            if not stack or stack.pop()!=pairs[ch]:return False
        i+=1
    return not stack and not quoted

def main():
    p=argparse.ArgumentParser();p.add_argument('--official-schema',type=Path);args=p.parse_args()
    schema=json.loads((ROOT/'schema/sharepoint-lists.json').read_text());assets=next(x for x in schema['lists'] if x['name']=='ITAssets')
    samples=json.loads((ROOT/'sample/assets_ready.sample.json').read_text());fields={f['name']:f for f in assets['fields']}
    assert len(samples)==16
    assert len({x['SerialKey'] for x in samples})==len(samples)
    for row in samples:
        assert row['SerialKey'].startswith('DEMO-')
        assert set(row)<=fields.keys()
        for f in assets['fields']:
            if f['required']:assert row.get(f['name']) is not None,f['name']
        assert row['HasExpiry']==bool(row['ExpiryDate'])
    fxfiles=list((ROOT/'powerfx').glob('*.fx'))
    for file in fxfiles:assert balanced(file.read_text()),f'Unbalanced delimiters: {file.name}'
    refs=[]
    for md in list(ROOT.glob('*.md'))+list((ROOT/'docs').glob('*.md')):
        assert not re.search('[ぁ-んァ-ン]',md.read_text()),f'Unexpected language in {md.name}'
        for target in re.findall(r'\]\(([^)]+)\)',md.read_text()):
            if target.startswith(('https:','http:','#')):continue
            assert (md.parent/target.split('#')[0]).exists(),f'Broken link {target} in {md.name}'
    result={'localSampleChecks':True,'sampleRows':20,'readyRows':16,'serialReviewRows':4,'powerFxDelimiterChecks':len(fxfiles),'powerFxCompiled':False,'powerAppsStudioValidated':False,'canvasPackageGenerated':False,'sharePointProvisioningExecuted':False,'flowsCreated':False,'realDataIncluded':False}
    if args.official_schema:
        import yaml,jsonschema
        official=yaml.safe_load(args.official_schema.read_text());example=yaml.safe_load((ROOT/'reference/format-example.pa.yaml').read_text())
        jsonschema.validators.validator_for(official)(official).validate(example)
        result['paYamlJsonSchemaStructureValid']=True;result['officialSchemaSha256']=hashlib.sha256(args.official_schema.read_bytes()).hexdigest()
    (ROOT/'validation-report.json').write_text(json.dumps(result,ensure_ascii=False,indent=2));print(json.dumps(result,ensure_ascii=False))
if __name__=='__main__':main()
