// Inside galAssets. AssetReadForEdit is a Power Apps (V2) flow, defined in docs/07.
Set(varAssetId, ThisItem.ID);
Set(varIsNew, false);
IfError(
    Set(varRead, AssetReadForEdit.Run(Text(varAssetId))),
    Set(varRead, {status: "Error", message: FirstError.Message, etag: "", assetJson: "{}"})
);
If(
    varRead.status = "Ok",
    Set(varJ, ParseJSON(varRead.assetJson));
    Set(varEdit, {
        ID: Value(Text(varJ.ID)),
        SerialNumber: Text(varJ.SerialNumber), SAPAssetNumber: Text(varJ.SAPAssetNumber),
        PCName: Text(varJ.PCName), Model: Text(varJ.Model),
        AssignedUserKOR: Text(varJ.AssignedUserKOR), AssignedUserENG: Text(varJ.AssignedUserENG),
        ADAccount: Text(varJ.ADAccount), LocationKey: Text(varJ.LocationKey),
        LocationRaw: Text(varJ.LocationRaw), LocationDetail: Text(varJ.LocationDetail),
        DeviceType: Text(varJ.DeviceType), AssetGroup: Text(varJ.AssetGroup),
        LifecycleState: Text(varJ.LifecycleState), AcquisitionState: Text(varJ.AcquisitionState),
        LanConnectorRaw: Text(varJ.LanConnectorRaw), ConsumablesRaw: Text(varJ.ConsumablesRaw),
        ChecklistRaw: Text(varJ.ChecklistRaw), Remarks: Text(varJ.Remarks),
        UsageMonths: If(IsBlank(Text(varJ.UsageMonths)), Blank(), Value(Text(varJ.UsageMonths))),
        StartDate: If(IsBlank(Text(varJ.StartDate)), Blank(), DateValue(Text(varJ.StartDate), "en-US")),
        ExpiryDate: If(IsBlank(Text(varJ.ExpiryDate)), Blank(), DateValue(Text(varJ.ExpiryDate), "en-US")),
        ExpirySource: Text(varJ.ExpirySource),
        LegacyNo: Text(varJ.LegacyNo), SourceSheet: Text(varJ.SourceSheet),
        SourceRow: Value(Text(varJ.SourceRow)), LegacyMetadata: Text(varJ.LegacyMetadata)
    });
    Set(varETag, varRead.etag);
    Set(varIsEditing, false); Set(varDirty, false); Set(varModalOpen, true);
    Reset(txtActionReason); Reset(txtSerial); Reset(txtSAP); Reset(txtPCName); Reset(txtModel);
    Reset(txtUserKOR); Reset(txtUserENG); Reset(txtAD); Reset(txtLocationRaw); Reset(txtLocationDetail);
    Reset(txtLan); Reset(txtConsumables); Reset(txtChecklist); Reset(txtRemarks); Reset(txtMonths);
    Reset(ddGroupEdit); Reset(ddLifecycleEdit); Reset(ddDeviceEdit); Reset(ddLocationEdit); Reset(ddAcquisitionEdit);
    Reset(chkHasStart); Reset(dpStart); Reset(chkExpiryExplicit); Reset(dpExpiry),
    Notify(Coalesce(varRead.message, "상세 정보를 가져오지 못했습니다"), NotificationType.Error)
)
