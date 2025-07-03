; 小工具組 NSIS 安裝腳本
; 編碼: UTF-8

; 基本設定
!define PRODUCT_NAME "小工具組"
!define PRODUCT_VERSION "1.0.0"
!define PRODUCT_PUBLISHER "李紘宇"
!define PRODUCT_WEB_SITE "https://your-website.com"
!define PRODUCT_DIR_REGKEY "Software\Microsoft\Windows\CurrentVersion\App Paths\小工具組.exe"
!define PRODUCT_UNINST_KEY "Software\Microsoft\Windows\CurrentVersion\Uninstall\${PRODUCT_NAME}"
!define PRODUCT_UNINST_ROOT_KEY "HKLM"

; 包含現代 UI
!include "MUI2.nsh"

; 設定安裝檔案屬性
Name "${PRODUCT_NAME} ${PRODUCT_VERSION}"
OutFile "ToolsInstaller.exe"
InstallDir "$PROGRAMFILES\${PRODUCT_NAME}"
InstallDirRegKey HKLM "${PRODUCT_DIR_REGKEY}" ""
ShowInstDetails show
ShowUnInstDetails show

; 要求管理員權限
RequestExecutionLevel admin

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
!define MUI_FINISHPAGE_RUN "$INSTDIR\小工具組.exe"
!insertmacro MUI_PAGE_FINISH

; 卸載頁面
!insertmacro MUI_UNPAGE_CONFIRM
!insertmacro MUI_UNPAGE_INSTFILES

; 語言設定
!insertmacro MUI_LANGUAGE "TradChinese"

; 版本資訊
VIProductVersion "1.0.0.0"
VIAddVersionKey /LANG=${LANG_TRADCHINESE} "ProductName" "${PRODUCT_NAME}"
VIAddVersionKey /LANG=${LANG_TRADCHINESE} "Comments" "小工具組安裝程式"
VIAddVersionKey /LANG=${LANG_TRADCHINESE} "CompanyName" "${PRODUCT_PUBLISHER}"
VIAddVersionKey /LANG=${LANG_TRADCHINESE} "LegalTrademarks" ""
VIAddVersionKey /LANG=${LANG_TRADCHINESE} "LegalCopyright" "c ${PRODUCT_PUBLISHER}"
VIAddVersionKey /LANG=${LANG_TRADCHINESE} "FileDescription" "${PRODUCT_NAME} 安裝程式"
VIAddVersionKey /LANG=${LANG_TRADCHINESE} "FileVersion" "${PRODUCT_VERSION}"
VIAddVersionKey /LANG=${LANG_TRADCHINESE} "ProductVersion" "${PRODUCT_VERSION}"

; 主要安裝區段
Section "主程式" SEC01
  SetOutPath "$INSTDIR"
  SetOverwrite ifnewer
  
  ; 複製主程式檔案
  File "dist\Tools\Tools.exe"
  
  ; 複製 _internal 目錄及其所有內容
  File /r "dist\Tools\_internal"
  
  ; 建立開始功能表捷徑
  CreateDirectory "$SMPROGRAMS\${PRODUCT_NAME}"
  CreateShortCut "$SMPROGRAMS\${PRODUCT_NAME}\${PRODUCT_NAME}.lnk" "$INSTDIR\小工具組.exe"
  CreateShortCut "$SMPROGRAMS\${PRODUCT_NAME}\卸載 ${PRODUCT_NAME}.lnk" "$INSTDIR\uninst.exe"
SectionEnd

; 桌面捷徑區段（可選）
Section "桌面捷徑" SEC02
  CreateShortCut "$DESKTOP\${PRODUCT_NAME}.lnk" "$INSTDIR\小工具組.exe"
SectionEnd

; 快速啟動捷徑區段（可選）
Section "快速啟動捷徑" SEC03
  CreateShortCut "$QUICKLAUNCH\${PRODUCT_NAME}.lnk" "$INSTDIR\小工具組.exe"
SectionEnd

; 區段描述
!insertmacro MUI_FUNCTION_DESCRIPTION_BEGIN
  !insertmacro MUI_DESCRIPTION_TEXT ${SEC01} "安裝 ${PRODUCT_NAME} 主程式檔案"
  !insertmacro MUI_DESCRIPTION_TEXT ${SEC02} "在桌面建立 ${PRODUCT_NAME} 捷徑"
  !insertmacro MUI_DESCRIPTION_TEXT ${SEC03} "在快速啟動列建立 ${PRODUCT_NAME} 捷徑"
!insertmacro MUI_FUNCTION_DESCRIPTION_END

; 安裝後處理
Section -AdditionalIcons
  WriteIniStr "$INSTDIR\${PRODUCT_NAME}.url" "InternetShortcut" "URL" "${PRODUCT_WEB_SITE}"
  CreateShortCut "$SMPROGRAMS\${PRODUCT_NAME}\官方網站.lnk" "$INSTDIR\${PRODUCT_NAME}.url"
SectionEnd

Section -Post
  WriteUninstaller "$INSTDIR\uninst.exe"
  WriteRegStr HKLM "${PRODUCT_DIR_REGKEY}" "" "$INSTDIR\小工具組.exe"
  WriteRegStr ${PRODUCT_UNINST_ROOT_KEY} "${PRODUCT_UNINST_KEY}" "DisplayName" "$(^Name)"
  WriteRegStr ${PRODUCT_UNINST_ROOT_KEY} "${PRODUCT_UNINST_KEY}" "UninstallString" "$INSTDIR\uninst.exe"
  WriteRegStr ${PRODUCT_UNINST_ROOT_KEY} "${PRODUCT_UNINST_KEY}" "DisplayIcon" "$INSTDIR\小工具組.exe"
  WriteRegStr ${PRODUCT_UNINST_ROOT_KEY} "${PRODUCT_UNINST_KEY}" "DisplayVersion" "${PRODUCT_VERSION}"
  WriteRegStr ${PRODUCT_UNINST_ROOT_KEY} "${PRODUCT_UNINST_KEY}" "URLInfoAbout" "${PRODUCT_WEB_SITE}"
  WriteRegStr ${PRODUCT_UNINST_ROOT_KEY} "${PRODUCT_UNINST_KEY}" "Publisher" "${PRODUCT_PUBLISHER}"
SectionEnd



; 卸載區段
Section Uninstall
  ; 刪除檔案和目錄
  Delete "$INSTDIR\${PRODUCT_NAME}.url"
  Delete "$INSTDIR\uninst.exe"
  Delete "$INSTDIR\小工具組.exe"
  
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
  ; 檢查是否已安裝
  ReadRegStr $R0 ${PRODUCT_UNINST_ROOT_KEY} "${PRODUCT_UNINST_KEY}" "UninstallString"
  StrCmp $R0 "" done
  
  MessageBox MB_OKCANCEL|MB_ICONEXCLAMATION \
  "${PRODUCT_NAME} 已經安裝。$\n$\n點擊「確定」移除先前版本，或點擊「取消」取消安裝。" \
  /SD IDOK IDOK uninst
  Abort
  
uninst:
  ClearErrors
  ExecWait '$R0 _?=$INSTDIR'
  
  IfErrors no_remove_uninstaller done
    no_remove_uninstaller:
    
done:
FunctionEnd

; 卸載前確認
Function un.onInit
  MessageBox MB_ICONQUESTION|MB_YESNO|MB_DEFBUTTON2 "您確定要完全移除 ${PRODUCT_NAME} 及其所有元件嗎？" /SD IDYES IDYES +2
  Abort
FunctionEnd

Function un.onUninstSuccess
  HideWindow
  MessageBox MB_ICONINFORMATION|MB_OK "${PRODUCT_NAME} 已成功從您的電腦移除。" /SD IDOK
FunctionEnd