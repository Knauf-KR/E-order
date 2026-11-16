Option Explicit
Dim shell, fso, root, appDir, bat, localDir, pythonw, logPath, cmd, rc
Set shell = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")
root = fso.GetParentFolderName(WScript.ScriptFullName)
appDir = fso.BuildPath(root, "ITAssetManager")
bat = fso.BuildPath(root, "launch.bat")
localDir = shell.ExpandEnvironmentStrings("%LOCALAPPDATA%")
If localDir = "%LOCALAPPDATA%" Then
  MsgBox "LOCALAPPDATA is unavailable. Please contact IT support.", 16, "Knauf IT Asset Manager"
  WScript.Quit 1
End If
If Not fso.FileExists(fso.BuildPath(appDir, "windowed.pyw")) Or Not fso.FileExists(bat) Then
  MsgBox "Keep launch.vbs, launch.bat and the ITAssetManager folder together beside the Excel workbook.", 16, "Knauf IT Asset Manager"
  WScript.Quit 1
End If
If Not fso.FolderExists(fso.BuildPath(localDir, "KnaufITAssetManager")) Then
  fso.CreateFolder fso.BuildPath(localDir, "KnaufITAssetManager")
End If
pythonw = fso.BuildPath(localDir, "KnaufITAssetManager\venv\Scripts\pythonw.exe")
logPath = fso.BuildPath(localDir, "KnaufITAssetManager\startup.log")
If Not fso.FileExists(pythonw) Then
  shell.Popup "Preparing the app for first use. This may take a few minutes. Please wait.", 3, "Knauf IT Asset Manager", 64
End If
' Run installation/checks hidden. setup-only never pauses or starts the GUI.
cmd = Quote(shell.ExpandEnvironmentStrings("%COMSPEC%")) & " /d /c " & Chr(34) & Quote(bat) & " --setup-only > " & Quote(logPath) & " 2>&1" & Chr(34)
On Error Resume Next
rc = shell.Run(cmd, 0, True)
If Err.Number <> 0 Then
  MsgBox "Windows could not start setup. Please contact IT support.", 16, "Knauf IT Asset Manager"
  WScript.Quit 1
End If
On Error GoTo 0
If rc <> 0 Or Not fso.FileExists(pythonw) Then
  MsgBox "Setup failed. Python 3.11+ with Python Launcher, pip and Tcl/Tk is required." & vbCrLf & vbCrLf & "Details: " & logPath, 16, "Knauf IT Asset Manager"
  WScript.Quit 1
End If
cmd = Quote(pythonw) & " " & Quote(fso.BuildPath(appDir, "windowed.pyw")) & " --asset-dir " & Quote(root)
On Error Resume Next
rc = shell.Run(cmd, 1, False)
If Err.Number <> 0 Then
  MsgBox "Windows could not open the app. Please contact IT support.", 16, "Knauf IT Asset Manager"
  WScript.Quit 1
End If
On Error GoTo 0
Function Quote(value)
  Quote = Chr(34) & value & Chr(34)
End Function
