// Timer: Duration=30000, Repeat=true, AutoStart=true. No push/real-time guarantee.
If(
    varModalOpen = false && varSaving = false,
    Set(varToday, Today());
    Refresh(ITAssets);
    Refresh(ITAssetSummary)
)
