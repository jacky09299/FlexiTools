; 小工具組 NSIS 安裝腳本
; 編碼: UTF-8
; 支援: 首次安裝、靜默更新、手動重複安裝

; 基本設定
!define PRODUCT_NAME "FlexiTools"
!define PRODUCT_VERSION "1.0.0"
!define PRODUCT_PUBLISHER "李紘宇"
!define PRODUCT_WEB_SITE "https://github.com/jacky09299/FlexiTools"
!define PRODUCT_DIR_REGKEY "Software\Microsoft\Windows\CurrentVersion\App Paths\FlexiTools.exe"
!define PRODUCT_UNINST_KEY "Software\Microsoft\Windows\CurrentVersion\Uninstall\${PRODUCT_NAME}"
!define PRODUCT_UNINST_ROOT_KEY "HKLM"

; 包含現代 UI
!include "MUI2.nsh"
!include "LogicLib.nsh"
!include "FileFunc.nsh"

; 設定安裝檔案屬性
Name "${PRODUCT_NAME} ${PRODUCT_VERSION}"
OutFile "FlexiToolsInstaller.exe"
InstallDir "$PROGRAMFILES\${PRODUCT_NAME}"
InstallDirRegKey HKLM "${PRODUCT_DIR_REGKEY}" ""
ShowInstDetails show
ShowUnInstDetails show

; 要求管理員權限
RequestExecutionLevel admin

; 靜默安裝支援
SilentInstall normal

; 介面設定
!define MUI_ABORTWARNING
!define MUI_ICON "tools.ico"
!define MUI_UNICON "tools.ico"

; 歡迎頁面
!insertmacro MUI_PAGE_WELCOME

; 授權協議頁面（可選）
; !insertmacro MUI_PAGE_LICENSE "license.txt"

; 選擇安裝目錄頁面
!insertmacro MUI_PAGE_DIRECTORY

; 選擇元件頁面
!insertmacro MUI_PAGE_COMPONENTS

; 安裝頁面
!insertmacro MUI_PAGE_INSTFILES

; 完成頁面
!define MUI_FINISHPAGE_RUN "$INSTDIR\FlexiTools.exe"
!insertmacro MUI_PAGE_FINISH

; 卸載頁面
!insertmacro MUI_UNPAGE_CONFIRM
!insertmacro MUI_UNPAGE_INSTFILES

; 語言設定
!insertmacro MUI_LANGUAGE "TradChinese"

; 版本資訊
VIProductVersion "1.0.0.0"
VIAddVersionKey /LANG=${LANG_TRADCHINESE} "ProductName" "${PRODUCT_NAME}"
VIAddVersionKey /LANG=${LANG_TRADCHINESE} "Comments" "FlexiToolsInstaller"
VIAddVersionKey /LANG=${LANG_TRADCHINESE} "CompanyName" "${PRODUCT_PUBLISHER}"
VIAddVersionKey /LANG=${LANG_TRADCHINESE} "LegalTrademarks" ""
VIAddVersionKey /LANG=${LANG_TRADCHINESE} "LegalCopyright" "c ${PRODUCT_PUBLISHER}"
VIAddVersionKey /LANG=${LANG_TRADCHINESE} "FileDescription" "${PRODUCT_NAME} 安裝程式"
VIAddVersionKey /LANG=${LANG_TRADCHINESE} "FileVersion" "${PRODUCT_VERSION}"
VIAddVersionKey /LANG=${LANG_TRADCHINESE} "ProductVersion" "${PRODUCT_VERSION}"

; 全域變數
Var IsUpdateMode
Var IsFirstInstall
Var SavesBackupPath

; 主要安裝區段
Section "Main Program" SEC01
  SetOutPath "$INSTDIR"
  SetOverwrite ifnewer
  
  ; 檢查是否為更新模式，如果是則備份 saves 資料夾
  ${If} $IsUpdateMode == "1"
    DetailPrint "Update mode detected, backing up user data..."
    IfFileExists "$INSTDIR\_internal\modules\saves\*.*" 0 +3
      CreateDirectory "$TEMP\FlexiTools_Backup"
      CopyFiles /SILENT "$INSTDIR\_internal\modules\saves\*.*" "$TEMP\FlexiTools_Backup"
      StrCpy $SavesBackupPath "$TEMP\FlexiTools_Backup"
  ${EndIf}
  
  ; 複製主程式檔案
  File "dist\FlexiTools\FlexiTools.exe"
  
  ; 建立版本檔案
  FileOpen $0 "$INSTDIR\version.txt" w
  FileWrite $0 "v${PRODUCT_VERSION}"
  FileClose $0
  
  ; 複製 _internal 目錄及其所有內容
  File /r "dist\FlexiTools\_internal"
  
  ; 如果是更新模式，恢復 saves 資料夾
  ${If} $IsUpdateMode == "1"
    ${AndIf} $SavesBackupPath != ""
      DetailPrint "Restoring user data..."
      CreateDirectory "$INSTDIR\_internal\modules\saves"
      CopyFiles /SILENT "$SavesBackupPath\*.*" "$INSTDIR\_internal\modules\saves"
      RMDir /r "$SavesBackupPath"
  ${EndIf}
  
  ; 只在首次安裝或手動安裝時建立捷徑
  ${If} $IsUpdateMode != "1"
    ; 建立開始功能表捷徑
    CreateDirectory "$SMPROGRAMS\${PRODUCT_NAME}"
    CreateShortCut "$SMPROGRAMS\${PRODUCT_NAME}\${PRODUCT_NAME}.lnk" "$INSTDIR\FlexiTools.exe"
    CreateShortCut "$SMPROGRAMS\${PRODUCT_NAME}\卸載 ${PRODUCT_NAME}.lnk" "$INSTDIR\uninst.exe"
  ${EndIf}
SectionEnd

; 桌面捷徑區段（可選）
Section "Desktop Shortcut" SEC02
  ; 只在非更新模式時建立桌面捷徑
  ${If} $IsUpdateMode != "1"
    CreateShortCut "$DESKTOP\${PRODUCT_NAME}.lnk" "$INSTDIR\FlexiTools.exe"
  ${EndIf}
SectionEnd

; 快速啟動捷徑區段（可選）
Section "Quick Launch Shortcut" SEC03
  ; 只在非更新模式時建立快速啟動捷徑
  ${If} $IsUpdateMode != "1"
    CreateShortCut "$QUICKLAUNCH\${PRODUCT_NAME}.lnk" "$INSTDIR\FlexiTools.exe"
  ${EndIf}
SectionEnd

; 區段描述
!insertmacro MUI_FUNCTION_DESCRIPTION_BEGIN
  !insertmacro MUI_DESCRIPTION_TEXT ${SEC01} "Install the main program files of ${PRODUCT_NAME}"
  !insertmacro MUI_DESCRIPTION_TEXT ${SEC02} "Create a ${PRODUCT_NAME} shortcut on the desktop"
  !insertmacro MUI_DESCRIPTION_TEXT ${SEC03} "Create a ${PRODUCT_NAME} shortcut in the Quick Launch bar"
!insertmacro MUI_FUNCTION_DESCRIPTION_END

; 安裝後處理
Section -AdditionalIcons
  ; 只在非更新模式時建立網站連結
  ${If} $IsUpdateMode != "1"
    WriteIniStr "$INSTDIR\${PRODUCT_NAME}.url" "InternetShortcut" "URL" "${PRODUCT_WEB_SITE}"
    CreateShortCut "$SMPROGRAMS\${PRODUCT_NAME}\官方網站.lnk" "$INSTDIR\${PRODUCT_NAME}.url"
  ${EndIf}
SectionEnd

Section -Post
  WriteUninstaller "$INSTDIR\uninst.exe"
  WriteRegStr HKLM "${PRODUCT_DIR_REGKEY}" "" "$INSTDIR\FlexiTools.exe"
  WriteRegStr ${PRODUCT_UNINST_ROOT_KEY} "${PRODUCT_UNINST_KEY}" "DisplayName" "$(^Name)"
  WriteRegStr ${PRODUCT_UNINST_ROOT_KEY} "${PRODUCT_UNINST_KEY}" "UninstallString" "$INSTDIR\uninst.exe"
  WriteRegStr ${PRODUCT_UNINST_ROOT_KEY} "${PRODUCT_UNINST_KEY}" "DisplayIcon" "$INSTDIR\FlexiTools.exe"
  WriteRegStr ${PRODUCT_UNINST_ROOT_KEY} "${PRODUCT_UNINST_KEY}" "DisplayVersion" "${PRODUCT_VERSION}"
  WriteRegStr ${PRODUCT_UNINST_ROOT_KEY} "${PRODUCT_UNINST_KEY}" "URLInfoAbout" "${PRODUCT_WEB_SITE}"
  WriteRegStr ${PRODUCT_UNINST_ROOT_KEY} "${PRODUCT_UNINST_KEY}" "Publisher" "${PRODUCT_PUBLISHER}"
SectionEnd

; 卸載區段
Section Uninstall
  ; 刪除檔案和目錄
  Delete "$INSTDIR\${PRODUCT_NAME}.url"
  Delete "$INSTDIR\uninst.exe"
  Delete "$INSTDIR\FlexiTools.exe"
  Delete "$INSTDIR\version.txt"
  
  ; 刪除 _internal 目錄
  RMDir /r "$INSTDIR\_internal"
  
  ; 刪除開始功能表項目
  Delete "$SMPROGRAMS\${PRODUCT_NAME}\卸載 ${PRODUCT_NAME}.lnk"
  Delete "$SMPROGRAMS\${PRODUCT_NAME}\官方網站.lnk"
  Delete "$SMPROGRAMS\${PRODUCT_NAME}\${PRODUCT_NAME}.lnk"
  RMDir "$SMPROGRAMS\${PRODUCT_NAME}"
  
  ; 刪除桌面捷徑
  Delete "$DESKTOP\${PRODUCT_NAME}.lnk"
  
  ; 刪除快速啟動捷徑
  Delete "$QUICKLAUNCH\${PRODUCT_NAME}.lnk"
  
  ; 刪除註冊表項目
  DeleteRegKey ${PRODUCT_UNINST_ROOT_KEY} "${PRODUCT_UNINST_KEY}"
  DeleteRegKey HKLM "${PRODUCT_DIR_REGKEY}"
  
  ; 刪除安裝目錄（如果為空）
  RMDir "$INSTDIR"
  
  SetAutoClose true
SectionEnd

; 安裝前檢查
Function .onInit
  ; 初始化變數
  StrCpy $IsUpdateMode "0"
  StrCpy $IsFirstInstall "1"
  StrCpy $SavesBackupPath ""
  
  ; 檢查命令列參數是否包含 /UPDATE
  ${GetOptions} $CMDLINE "/UPDATE" $R0
  IfErrors +3 0
    StrCpy $IsUpdateMode "1"
    SetSilent silent
  
  ; 檢查是否已安裝
  ReadRegStr $R0 ${PRODUCT_UNINST_ROOT_KEY} "${PRODUCT_UNINST_KEY}" "UninstallString"
  StrCmp $R0 "" first_install
  
  ; 已安裝，設定為非首次安裝
  StrCpy $IsFirstInstall "0"
  
  ; 如果是更新模式，直接繼續安裝
  ${If} $IsUpdateMode == "1"
    Goto done
  ${EndIf}
  
  ; 手動安裝模式：詢問是否卸載舊版
  MessageBox MB_OKCANCEL|MB_ICONEXCLAMATION \
  "${PRODUCT_NAME} is already installed.$\n$\nClick OK to remove the previous version or Cancel to cancel this installation." \
  /SD IDOK IDOK uninst
  Abort
  
uninst:
  ClearErrors
  ExecWait '$R0 _?=$INSTDIR'
  
  IfErrors no_remove_uninstaller done
    no_remove_uninstaller:
    
  Goto done
  
first_install:
  ; 首次安裝
  StrCpy $IsFirstInstall "1"
  
done:
FunctionEnd

; 卸載前確認
Function un.onInit
  MessageBox MB_ICONQUESTION|MB_YESNO|MB_DEFBUTTON2 "Are you sure you want to completely remove ${PRODUCT_NAME} and all of its components?" /SD IDYES IDYES +2
  Abort
FunctionEnd

Function un.onUninstSuccess
  HideWindow
  MessageBox MB_ICONINFORMATION|MB_OK "${PRODUCT_NAME} has been successfully removed from your computer." /SD IDOK
FunctionEnd