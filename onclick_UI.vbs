' MarkItDown GUI launcher (silent on success, error dialog on failure).
'
' Why a .vbs and not a .bat:
'   - .bat with `start "" pythonw.exe` flashes a console window and detaches,
'     so any startup error (import failure, missing Qt plugin, blocked binary)
'     disappears silently and the user just sees a flash with no GUI.
'   - This script runs pythonw.exe with no console at all, captures stderr to
'     a log file, and pops up a MsgBox with the captured error if pythonw
'     exits non-zero. On success it is fully invisible.

Option Explicit

Dim fso, shell, scriptDir, pyw, pyc, gui
Dim tempDir, logFile, q, inner, cmdLine, rc
Dim msg, stream, contents

Set fso = CreateObject("Scripting.FileSystemObject")
Set shell = CreateObject("WScript.Shell")

scriptDir = fso.GetParentFolderName(WScript.ScriptFullName)
pyw = scriptDir & "\python312\pythonw.exe"
pyc = scriptDir & "\python312\python.exe"
tempDir = shell.ExpandEnvironmentStrings("%TEMP%")
logFile = tempDir & "\markitdown_gui_error.log"

If Not fso.FileExists(pyc) Then
    MsgBox "Portable Python runtime not found at:" & vbCrLf & _
           scriptDir & "\python312" & vbCrLf & vbCrLf & _
           "This launcher expects the bundled python312\ folder shipped with " & _
           "the integrated package. If you cloned from git, download the " & _
           "integrated package release instead.", _
           vbCritical, "MarkItDown GUI"
    WScript.Quit 1
End If

If fso.FileExists(pyw) Then
    gui = pyw
Else
    gui = pyc
End If

' Wrap in `cmd /c "..."` so we can redirect pythonw's stderr to a file.
' shell.Run window style 0 hides the wrapping cmd window; pythonw still
' shows its own GUI window normally.
q = Chr(34)
inner = q & gui & q & " -m markitdown_gui 2> " & q & logFile & q
cmdLine = "cmd /c " & q & inner & q

rc = shell.Run(cmdLine, 0, True)

If rc <> 0 Then
    contents = ""
    If fso.FileExists(logFile) Then
        Set stream = fso.OpenTextFile(logFile, 1)
        If Not stream.AtEndOfStream Then
            contents = stream.ReadAll()
        End If
        stream.Close
    End If

    msg = "MarkItDown GUI failed to start (exit code " & rc & ")."
    If Len(contents) > 0 Then
        msg = msg & vbCrLf & vbCrLf & "Error output:" & vbCrLf & contents
    End If
    msg = msg & vbCrLf & "Log file: " & logFile & vbCrLf & vbCrLf & _
          "For full diagnostic output, run onclick_UI_debug.bat."
    MsgBox msg, vbCritical, "MarkItDown GUI"
End If
