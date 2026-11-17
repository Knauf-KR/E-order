// AssetSearchSnapshot flow: complete(Boolean), recordsJson/message/snapshotAt(Text).
Set(varSnapshotComplete,false);
IfError(
    Set(varSnapshotResponse,AssetSearchSnapshot.Run()),
    Set(varSnapshotResponse,{complete:false,recordsJson:"[]",message:FirstError.Message,snapshotAt:""})
);
If(
    varSnapshotResponse.complete,
    IfError(
    ClearCollect(colSnapshot,
        ForAll(Table(ParseJSON(varSnapshotResponse.recordsJson)) As parsed,
            {ID: Value(Text(parsed.Value.ID)),
             AssetKey: Text(parsed.Value.AssetKey),
             SerialNumber: Text(parsed.Value.SerialNumber),
             SerialKey: Text(parsed.Value.SerialKey),
             SAPAssetNumber: Text(parsed.Value.SAPAssetNumber),
             PCName: Text(parsed.Value.PCName),
             Model: Text(parsed.Value.Model),
             AssignedUserKOR: Text(parsed.Value.AssignedUserKOR),
             AssignedUserENG: Text(parsed.Value.AssignedUserENG),
             ADAccount: Text(parsed.Value.ADAccount),
             LocationKey: Text(parsed.Value.LocationKey),
             LocationRaw: Text(parsed.Value.LocationRaw),
             LocationDetail: Text(parsed.Value.LocationDetail),
             DeviceTypeRaw: Text(parsed.Value.DeviceTypeRaw),
             LanConnectorRaw: Text(parsed.Value.LanConnectorRaw),
             ConsumablesRaw: Text(parsed.Value.ConsumablesRaw),
             ChecklistRaw: Text(parsed.Value.ChecklistRaw),
             LegacyNo: Text(parsed.Value.LegacyNo),
             SourceSheet: Text(parsed.Value.SourceSheet),
             LegacyStartText: Text(parsed.Value.LegacyStartText),
             LegacyExpiryText: Text(parsed.Value.LegacyExpiryText),
             LegacyRemainingText: Text(parsed.Value.LegacyRemainingText),
             LastRequestId: Text(parsed.Value.LastRequestId),
             AssetGroup: Text(parsed.Value.AssetGroup),
             LifecycleState: Text(parsed.Value.LifecycleState),
             DeviceType: Text(parsed.Value.DeviceType),
             AcquisitionState: Text(parsed.Value.AcquisitionState),
             ExpirySource: Text(parsed.Value.ExpirySource),
             StartDate: If(IsBlank(Text(parsed.Value.StartDate)), Blank(), DateValue(Text(parsed.Value.StartDate), "en-US")),
             ExpiryDate: If(IsBlank(Text(parsed.Value.ExpiryDate)), Blank(), DateValue(Text(parsed.Value.ExpiryDate), "en-US")),
             RetiredOn: If(IsBlank(Text(parsed.Value.RetiredOn)), Blank(), DateValue(Text(parsed.Value.RetiredOn), "en-US")),
             UsageMonths: If(IsBlank(Text(parsed.Value.UsageMonths)), Blank(), Value(Text(parsed.Value.UsageMonths))),
             HasExpiry: Boolean(parsed.Value.HasExpiry),
             HasDataIssues: Boolean(parsed.Value.HasDataIssues),
             IsDeleted: Boolean(parsed.Value.IsDeleted),
             SourceRow: If(IsBlank(Text(parsed.Value.SourceRow)), Blank(), Value(Text(parsed.Value.SourceRow))),
             Remarks: Text(parsed.Value.Remarks),
             IssueCodes: Text(parsed.Value.IssueCodes),
             LegacyMetadata: Text(parsed.Value.LegacyMetadata)}
        )
    );
    Set(varSnapshotComplete,true),
    Clear(colSnapshot); Set(varSnapshotComplete,false); Notify("스냅샷 변환에 실패했습니다.",NotificationType.Error)
    ),
    Clear(colSnapshot); Notify(Coalesce(varSnapshotResponse.message,"전체 데이터를 가져오지 못했습니다"),NotificationType.Warning)
)
