# Only the bundled fictional sample data; no arbitrary input path accepted.
param([string]$SiteUrl,[string]$ClientId,[switch]$Apply)
$ErrorActionPreference='Stop'
$root=Split-Path $PSScriptRoot -Parent
$groups=@(
    @{List='ITLocations';File='ITLocations.sample.json';Key='LocationKey'},
    @{List='ITAssetStaging';File='staging.sample.json';Key='SourceKey'},
    @{List='ITAssets';File='assets_ready.sample.json';Key='AssetKey'}
)
$schema=Get-Content (Join-Path $root 'schema/sharepoint-lists.json') -Raw | ConvertFrom-Json
if ($Apply) {
    if (-not $SiteUrl -or -not $ClientId) {throw 'Approved development SiteUrl and ClientId required.'}
    Import-Module PnP.PowerShell -ErrorAction Stop
    Connect-PnPOnline -Url $SiteUrl -Interactive -ClientId $ClientId
}
foreach ($group in $groups) {
    $rows=Get-Content (Join-Path $root ('sample/'+$group.File)) -Raw | ConvertFrom-Json
    foreach ($row in $rows) {
        if ($row.SerialKey -and -not $row.SerialKey.StartsWith('DEMO-')) {throw 'Only bundled fictional DEMO records are permitted.'}
    }
    Write-Host ("{0}: {1} fictional rows" -f $group.List,$rows.Count)
    if (-not $Apply) {continue}
    $definition=$schema.lists | Where-Object name -eq $group.List
    foreach ($row in $rows) {
        $key=[System.Security.SecurityElement]::Escape([string]$row.($group.Key))
        $query="<View><Query><Where><Eq><FieldRef Name='$($group.Key)'/><Value Type='Text'>$key</Value></Eq></Where></Query><RowLimit>1</RowLimit></View>"
        if (Get-PnPListItem -List $group.List -Query $query) {Write-Host 'SKIP existing sample key';continue}
        $values=@{}
        foreach ($field in $definition.fields) {
            $property=$row.PSObject.Properties[$field.name]
            if (-not $property) {continue}
            $v=$property.Value
            if ($null -ne $v -and $field.type -eq 'Date') {
                $d=[datetime]::ParseExact([string]$v,'yyyy-MM-dd',[System.Globalization.CultureInfo]::InvariantCulture)
                $d=[datetime]::SpecifyKind($d,[DateTimeKind]::Unspecified)
                try {$tz=[TimeZoneInfo]::FindSystemTimeZoneById('Korea Standard Time')} catch {$tz=[TimeZoneInfo]::FindSystemTimeZoneById('Asia/Seoul')}
                $v=[TimeZoneInfo]::ConvertTimeToUtc($d,$tz)
            }
            $values[$field.name]=$v
        }
        $values.Title=if ($row.Title) {$row.Title} elseif ($row.PCName) {$row.PCName} else {[string]$row.($group.Key)}
        Add-PnPListItem -List $group.List -Values $values | Out-Null
    }
}
if (-not $Apply) {Write-Host 'Dry-run only: no tenant changes.'}
