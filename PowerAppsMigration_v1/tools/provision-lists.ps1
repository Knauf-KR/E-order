# Optional PnP community tooling; never run automatically. PowerShell 7 + PnP.PowerShell required.
# Dry-run by default. Sample developer site only for initial use.
param([string]$SiteUrl, [string]$ClientId, [switch]$Apply)
$ErrorActionPreference = 'Stop'
$schema = Get-Content (Join-Path $PSScriptRoot '../schema/sharepoint-lists.json') -Raw | ConvertFrom-Json
if (-not $Apply) {
    $schema.lists | ForEach-Object { Write-Host ("PLAN {0}: {1} fields [{2}]" -f $_.name, $_.fields.Count, $_.phase) }
    Write-Host 'No tenant changes. Review schema, then pass -SiteUrl -ClientId -Apply in an approved development site.'
    exit 0
}
if (-not $SiteUrl -or -not $ClientId) { throw 'SiteUrl and approved Entra application ClientId are required.' }
Import-Module PnP.PowerShell -ErrorAction Stop
Connect-PnPOnline -Url $SiteUrl -Interactive -ClientId $ClientId
foreach ($list in $schema.lists) {
    $existing = Get-PnPList -Identity $list.name -ErrorAction SilentlyContinue
    if (-not $existing) { New-PnPList -Title $list.name -Template GenericList -OnQuickLaunch | Out-Null }
    Set-PnPList -Identity $list.name -EnableVersioning $true | Out-Null
    Set-PnPField -List $list.name -Identity 'Title' -Values @{Required=$false} | Out-Null
    foreach ($field in $list.fields) {
        $existingField = Get-PnPField -List $list.name -Identity $field.name -ErrorAction SilentlyContinue
        if ($existingField) { Write-Host "SKIP existing field $($list.name).$($field.name) (verify type manually)"; continue }
        $kind = switch ($field.type) { 'Date' {'DateTime'} 'DateTime' {'DateTime'} 'Note' {'Note'} 'Number' {'Number'} 'Boolean' {'Boolean'} default {'Text'} }
        $format = if ($field.type -eq 'Date') { ' Format="DateOnly"' } elseif ($field.type -eq 'Note') { ' RichText="FALSE" NumLines="6"' } else { '' }
        $label = [System.Security.SecurityElement]::Escape($field.label)
        $required = if ($field.required) {'TRUE'} else {'FALSE'}
        $xml = "<Field Type=`"$kind`" Name=`"$($field.name)`" StaticName=`"$($field.name)`" DisplayName=`"$label`" Required=`"$required`"$format />"
        Add-PnPFieldFromXml -List $list.name -FieldXml $xml | Out-Null
        if ($field.indexed) { Set-PnPField -List $list.name -Identity $field.name -Values @{Indexed=$true} | Out-Null }
        if ($field.unique) { Set-PnPField -List $list.name -Identity $field.name -Values @{EnforceUniqueValues=$true} | Out-Null }
    }
}
foreach ($library in $schema.libraries) {
    if (-not (Get-PnPList -Identity $library.name -ErrorAction SilentlyContinue)) { New-PnPList -Title $library.name -Template DocumentLibrary | Out-Null }
}
Write-Host 'Provisioned definitions only. No asset data imported; permissions/flows/app still require configuration.'
