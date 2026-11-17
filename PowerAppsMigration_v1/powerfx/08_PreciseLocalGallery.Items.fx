// Only after AssetSearchSnapshot confirms Complete=true (docs/07).
// Do not ClearCollect(ITAssets) and assume it contains the whole list.
If(
    varSnapshotComplete,
    Filter(
        colSnapshot As a,
        IsDeleted = false,
        (varGroup = "" || AssetGroup = varGroup),
        (varLifecycle = "" || LifecycleState = varLifecycle),
        (varDevice = "" || DeviceType = varDevice),
        (varLocation = "" || LocationKey = varLocation),
        (varQualityOnly = false || HasDataIssues = true),
        (
            varExpiryMode = "All" ||
            (varExpiryMode = "Expired" && HasExpiry = true && ExpiryDate < varToday &&
                (LifecycleState = "InUse" || LifecycleState = "Stock")) ||
            (varExpiryMode = "Due30" && HasExpiry = true && ExpiryDate >= varToday &&
                ExpiryDate <= DateAdd(varToday, 30, TimeUnit.Days) &&
                (LifecycleState = "InUse" || LifecycleState = "Stock")) ||
            (varExpiryMode = "Due60" && HasExpiry = true && ExpiryDate >= varToday &&
                ExpiryDate <= DateAdd(varToday, 60, TimeUnit.Days) &&
                (LifecycleState = "InUse" || LifecycleState = "Stock")) ||
            (varExpiryMode = "Due90" && HasExpiry = true && ExpiryDate >= varToday &&
                ExpiryDate <= DateAdd(varToday, 90, TimeUnit.Days) &&
                (LifecycleState = "InUse" || LifecycleState = "Stock")) ||
            (varExpiryMode = "Missing" && HasExpiry = false &&
                (LifecycleState = "InUse" || LifecycleState = "Stock")) ||
            (varExpiryMode = "Retired" && LifecycleState = "Retired")
        ),
        CountIf(
            Split(varSearch, " ") As token,
            IsBlank(token.Value) ||
            Lower(token.Value) in Lower(Concatenate(
                a.SerialNumber, " ", a.SAPAssetNumber, " ", a.PCName, " ", a.Model, " ",
                a.AssignedUserKOR, " ", a.AssignedUserENG, " ", a.ADAccount, " ",
                a.LocationRaw, " ", a.LocationDetail, " ", a.Remarks, " ",
                a.LanConnectorRaw, " ", a.ConsumablesRaw, " ", a.ChecklistRaw, " ",
                a.DeviceTypeRaw, " ", a.LegacyNo, " ", a.SourceSheet, " ",
                a.LegacyStartText, " ", a.LegacyExpiryText, " ", a.LegacyRemainingText
            ))
        ) = CountRows(Split(varSearch, " "))
    ),
    Filter(colSnapshot, false)
)
