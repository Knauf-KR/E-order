// ITAssets fields in this formula are Text / Boolean / Date, not Choice/Lookup.
// Prefix search deliberately differs from the legacy all-token substring search.
// Test delegation with the app data-row limit set to 1, then with >2,000 mock rows.
SortByColumns(
    Filter(
        ITAssets,
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
        (
            varSearch = "" ||
            StartsWith(PCName, varSearch) ||
            StartsWith(SerialKey, varSearchKey) ||
            StartsWith(SAPAssetNumber, varSearch) ||
            StartsWith(Model, varSearch) ||
            StartsWith(AssignedUserKOR, varSearch) ||
            StartsWith(AssignedUserENG, varSearch) ||
            StartsWith(LocationRaw, varSearch) ||
            StartsWith(ADAccount, varSearch)
        )
    ),
    "PCName", SortOrder.Ascending
)
