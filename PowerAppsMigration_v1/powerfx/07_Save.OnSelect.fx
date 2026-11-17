// Defaults/Items/OnChange for every referenced control: docs/03_UI and docs/07.
// No client-supplied SerialKey is trusted: AssetWrite recomputes it.
Set(varSerialKey, Upper(Substitute(Substitute(Substitute(Substitute(Substitute(
    Trim(txtSerial.Text), " ", ""), Char(160), ""), Char(9), ""), Char(10), ""), Char(13), "")));
Set(varMonthsValue, IfError(Value(Trim(txtMonths.Text)), Blank()));
If(
    IsBlank(varSerialKey) || Len(varSerialKey) > 255 || !IsMatch(varSerialKey, "^[A-Z0-9-]+$"),
    Notify("S/N을 확인하세요. 영문·숫자·하이픈을 사용하며 O/0은 구분합니다.", NotificationType.Error),
    !IsBlank(Trim(txtMonths.Text)) &&
        (IsBlank(varMonthsValue) || varMonthsValue < 1 || varMonthsValue > 1200 || Mod(varMonthsValue, 1) <> 0),
    Notify("사용기간은 1~1200의 정수입니다.", NotificationType.Error),
    chkHasStart.Value && chkExpiryExplicit.Value && dpExpiry.SelectedDate < dpStart.SelectedDate,
    Notify("만료일이 시작일보다 빠릅니다.", NotificationType.Error),
    Set(varDuplicateId, LookUp(ITAssets, SerialKey = varSerialKey, ID));
    If(
        !IsBlank(varDuplicateId) && (varIsNew || varDuplicateId <> varAssetId),
        Notify("동일한 S/N이 있습니다. 폐기 자산도 확인하세요.", NotificationType.Error),
        Set(varSaving, true);
        Set(varRequestId, Text(GUID()));
        Set(varPayload, JSON({
            RequestId: varRequestId, ActionReason: txtActionReason.Text,
            SerialNumber: txtSerial.Text, SAPAssetNumber: txtSAP.Text,
            PCName: txtPCName.Text, Model: txtModel.Text,
            AssignedUserKOR: txtUserKOR.Text, AssignedUserENG: txtUserENG.Text,
            ADAccount: txtAD.Text, LocationKey: ddLocationEdit.Selected.LocationKey,
            LocationRaw: txtLocationRaw.Text, LocationDetail: txtLocationDetail.Text,
            AssetGroup: ddGroupEdit.Selected.Code, LifecycleState: ddLifecycleEdit.Selected.Code,
            DeviceType: ddDeviceEdit.Selected.Code, AcquisitionState: ddAcquisitionEdit.Selected.Code,
            LanConnectorRaw: txtLan.Text, ConsumablesRaw: txtConsumables.Text,
            ChecklistRaw: txtChecklist.Text, Remarks: txtRemarks.Text,
            UsageMonths: If(IsBlank(Trim(txtMonths.Text)), Blank(), varMonthsValue),
            StartDate: If(chkHasStart.Value, Text(dpStart.SelectedDate, "[$-en-US]yyyy-mm-dd"), Blank()),
            ExplicitExpiryDate: If(chkExpiryExplicit.Value, Text(dpExpiry.SelectedDate, "[$-en-US]yyyy-mm-dd"), Blank())
        }, JSONFormat.Compact));
        IfError(
            Set(varSaveResponse, AssetWrite.Run(varPayload, If(varIsNew, "", varETag), If(varIsNew, "", Text(varAssetId)))),
            Set(varSaveResponse, {status: "Unknown", message: FirstError.Message, id: "", etag: ""})
        );
        Set(varSaving, false);
        Switch(
            varSaveResponse.status,
            "Ok", Set(varDirty, false); Set(varModalOpen, false); Refresh(ITAssets); Notify("저장했습니다.", NotificationType.Success),
            "Conflict", Notify("다른 사용자가 변경했습니다. 입력 내용을 보관하고 다시 열어 적용하세요.", NotificationType.Warning),
            "DuplicateSerial", Notify("다른 요청이 먼저 같은 S/N을 저장했습니다. 입력 내용은 유지합니다.", NotificationType.Error),
            "Unknown", Notify("저장 결과를 확인할 수 없습니다. 요청 키를 기록하고 다시 조회하세요: " & varRequestId, NotificationType.Warning),
            Notify(Coalesce(varSaveResponse.message, "저장하지 못했습니다."), NotificationType.Error)
        )
    )
)
