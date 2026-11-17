Set(varIsNew, true); Set(varAssetId, 0); Set(varETag, "");
// The snapshot shape is initialized without company data.
Set(varEdit, {ID: 0, SerialNumber: "", SAPAssetNumber: "", PCName: "", Model: "",
    AssignedUserKOR: "", AssignedUserENG: "", ADAccount: "", LocationKey: "Unknown", LocationRaw: "", LocationDetail: "",
    DeviceType: "Unknown", AssetGroup: If(varGroup = "", "Office", varGroup), LifecycleState: If(varLifecycle = "", "InUse", varLifecycle),
    AcquisitionState: "Unknown", LanConnectorRaw: "", ConsumablesRaw: "", ChecklistRaw: "", Remarks: "",
    UsageMonths: 48, StartDate: Blank(), ExpiryDate: Blank(), ExpirySource: "Unknown",
    LegacyNo: "", SourceSheet: "", SourceRow: 0, LegacyMetadata: ""});
Set(varIsEditing, true); Set(varDirty, false); Set(varModalOpen, true);
Reset(txtActionReason); Reset(txtSerial); Reset(txtSAP); Reset(txtPCName); Reset(txtModel);
Reset(txtUserKOR); Reset(txtUserENG); Reset(txtAD); Reset(txtLocationRaw); Reset(txtLocationDetail);
Reset(txtLan); Reset(txtConsumables); Reset(txtChecklist); Reset(txtRemarks); Reset(txtMonths);
Reset(ddGroupEdit); Reset(ddLifecycleEdit); Reset(ddDeviceEdit); Reset(ddLocationEdit); Reset(ddAcquisitionEdit);
Reset(chkHasStart); Reset(dpStart); Reset(chkExpiryExplicit); Reset(dpExpiry)
