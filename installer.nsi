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
!include "Sections.nsh"
; !include "nsProcess.nsh" ; Uncomment if using nsProcess plugin for more robust process handling

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

; --- Page 1: Shortcuts and Core ---
!define MUI_PAGE_HEADER_TEXT "Select Components"
!define MUI_PAGE_HEADER_SUBTEXT "Choose which features of ${PRODUCT_NAME} you want to install."
!define MUI_PAGE_CUSTOMFUNCTION_PRE PrePageShortcuts
!insertmacro MUI_PAGE_COMPONENTS

; --- Page 2: Modules ---
!define MUI_PAGE_HEADER_TEXT "Select Modules"
!define MUI_PAGE_HEADER_SUBTEXT "Choose which modules you want to include."
!define MUI_PAGE_CUSTOMFUNCTION_PRE PrePageModules
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

; 主要安裝區段
Section "Main Program" SEC01
  SectionIn RO ; Read-Only, cannot be unselected
  SetOutPath "$INSTDIR"
  SetOverwrite ifnewer

  ; 複製主程式檔案
  File "dist\FlexiTools\FlexiTools.exe"

  ; 建立版本檔案
  FileOpen $0 "$INSTDIR\version.txt" w
  FileWrite $0 "v${PRODUCT_VERSION}"
  FileClose $0

  ; 複製 _internal 目錄及其所有內容，但排除 modules
  ; NSIS File /r /x copies recursively excluding pattern.
  ; We want to copy everything in _internal EXCEPT the modules content
  ; Because PyInstaller puts modules in _internal\modules

  SetOutPath "$INSTDIR\_internal"
  File /r /x "modules" "dist\FlexiTools\_internal\*.*"

  ; Create modules directory structure but don't copy all py files yet
  CreateDirectory "$INSTDIR\_internal\modules"
  SetOutPath "$INSTDIR\_internal\modules"

  ; Copy __init__.py or other critical files if they exist and are not optional modules
  ; For now we assume .py files in modules root are the optional ones
  ; But subdirectories (like saves) need to be handled?
  ; saves is user data and should be in AppData now, so we don't worry about overwriting it here.

  ; Copy non-python files in modules just in case (e.g. assets inside modules folder?)
  File /r /x "*.py" "dist\FlexiTools\_internal\modules\*.*"

  ; 只在首次安裝或手動安裝時建立捷徑
  ${If} $IsUpdateMode != "1"
    ; 建立開始功能表捷徑
    CreateDirectory "$SMPROGRAMS\${PRODUCT_NAME}"
    CreateShortCut "$SMPROGRAMS\${PRODUCT_NAME}\${PRODUCT_NAME}.lnk" "$INSTDIR\FlexiTools.exe"
    CreateShortCut "$SMPROGRAMS\${PRODUCT_NAME}\卸載 ${PRODUCT_NAME}.lnk" "$INSTDIR\uninst.exe"
  ${EndIf}
SectionEnd


Section "Fitter" SEC_MOD_0
  SetOutPath "$INSTDIR\_internal\modules"
  File "dist\FlexiTools\_internal\modules\Fitter.py"
SectionEnd


Section "browser" SEC_MOD_1
  SetOutPath "$INSTDIR\_internal\modules"
  File "dist\FlexiTools\_internal\modules\browser.py"
SectionEnd


Section "clock" SEC_MOD_2
  SetOutPath "$INSTDIR\_internal\modules"
  File "dist\FlexiTools\_internal\modules\clock.py"
SectionEnd


Section "color_palette" SEC_MOD_3
  SetOutPath "$INSTDIR\_internal\modules"
  File "dist\FlexiTools\_internal\modules\color_palette.py"
SectionEnd


Section "draw" SEC_MOD_4
  SetOutPath "$INSTDIR\_internal\modules"
  File "dist\FlexiTools\_internal\modules\draw.py"
SectionEnd


Section "exe_embedder" SEC_MOD_5
  SetOutPath "$INSTDIR\_internal\modules"
  File "dist\FlexiTools\_internal\modules\exe_embedder.py"
SectionEnd


Section "gui_cmd" SEC_MOD_6
  SetOutPath "$INSTDIR\_internal\modules"
  File "dist\FlexiTools\_internal\modules\gui_cmd.py"
SectionEnd


Section "image_editor" SEC_MOD_7
  SetOutPath "$INSTDIR\_internal\modules"
  File "dist\FlexiTools\_internal\modules\image_editor.py"
SectionEnd


Section "mp4_processor" SEC_MOD_8
  SetOutPath "$INSTDIR\_internal\modules"
  File "dist\FlexiTools\_internal\modules\mp4_processor.py"
SectionEnd


Section "notepad" SEC_MOD_9
  SetOutPath "$INSTDIR\_internal\modules"
  File "dist\FlexiTools\_internal\modules\notepad.py"
SectionEnd


Section "pdf_processor" SEC_MOD_10
  SetOutPath "$INSTDIR\_internal\modules"
  File "dist\FlexiTools\_internal\modules\pdf_processor.py"
SectionEnd


Section "pdf_viewer" SEC_MOD_11
  SetOutPath "$INSTDIR\_internal\modules"
  File "dist\FlexiTools\_internal\modules\pdf_viewer.py"
SectionEnd


Section "plot_gui" SEC_MOD_12
  SetOutPath "$INSTDIR\_internal\modules"
  File "dist\FlexiTools\_internal\modules\plot_gui.py"
SectionEnd


Section "py_gui_runner" SEC_MOD_13
  SetOutPath "$INSTDIR\_internal\modules"
  File "dist\FlexiTools\_internal\modules\py_gui_runner.py"
SectionEnd


Section "recipe_wheel" SEC_MOD_14
  SetOutPath "$INSTDIR\_internal\modules"
  File "dist\FlexiTools\_internal\modules\recipe_wheel.py"
SectionEnd


Section "report" SEC_MOD_15
  SetOutPath "$INSTDIR\_internal\modules"
  File "dist\FlexiTools\_internal\modules\report.py"
SectionEnd


Section "split_para" SEC_MOD_16
  SetOutPath "$INSTDIR\_internal\modules"
  File "dist\FlexiTools\_internal\modules\split_para.py"
SectionEnd


Section "sudoku_studio" SEC_MOD_17
  SetOutPath "$INSTDIR\_internal\modules"
  File "dist\FlexiTools\_internal\modules\sudoku_studio.py"
SectionEnd


Section "system_info" SEC_MOD_18
  SetOutPath "$INSTDIR\_internal\modules"
  File "dist\FlexiTools\_internal\modules\system_info.py"
SectionEnd


Section "template_module" SEC_MOD_19
  SetOutPath "$INSTDIR\_internal\modules"
  File "dist\FlexiTools\_internal\modules\template_module.py"
SectionEnd


Section "todo_list" SEC_MOD_20
  SetOutPath "$INSTDIR\_internal\modules"
  File "dist\FlexiTools\_internal\modules\todo_list.py"
SectionEnd


Section "translator" SEC_MOD_21
  SetOutPath "$INSTDIR\_internal\modules"
  File "dist\FlexiTools\_internal\modules\translator.py"
SectionEnd


Section "unit_converter" SEC_MOD_22
  SetOutPath "$INSTDIR\_internal\modules"
  File "dist\FlexiTools\_internal\modules\unit_converter.py"
SectionEnd


Section "video" SEC_MOD_23
  SetOutPath "$INSTDIR\_internal\modules"
  File "dist\FlexiTools\_internal\modules\video.py"
SectionEnd


Section "youtube_downloader" SEC_MOD_24
  SetOutPath "$INSTDIR\_internal\modules"
  File "dist\FlexiTools\_internal\modules\youtube_downloader.py"
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
  !insertmacro MUI_DESCRIPTION_TEXT ${SEC_MOD_0} "Install Fitter module"
  !insertmacro MUI_DESCRIPTION_TEXT ${SEC_MOD_1} "Install browser module"
  !insertmacro MUI_DESCRIPTION_TEXT ${SEC_MOD_2} "Install clock module"
  !insertmacro MUI_DESCRIPTION_TEXT ${SEC_MOD_3} "Install color_palette module"
  !insertmacro MUI_DESCRIPTION_TEXT ${SEC_MOD_4} "Install draw module"
  !insertmacro MUI_DESCRIPTION_TEXT ${SEC_MOD_5} "Install exe_embedder module"
  !insertmacro MUI_DESCRIPTION_TEXT ${SEC_MOD_6} "Install gui_cmd module"
  !insertmacro MUI_DESCRIPTION_TEXT ${SEC_MOD_7} "Install image_editor module"
  !insertmacro MUI_DESCRIPTION_TEXT ${SEC_MOD_8} "Install mp4_processor module"
  !insertmacro MUI_DESCRIPTION_TEXT ${SEC_MOD_9} "Install notepad module"
  !insertmacro MUI_DESCRIPTION_TEXT ${SEC_MOD_10} "Install pdf_processor module"
  !insertmacro MUI_DESCRIPTION_TEXT ${SEC_MOD_11} "Install pdf_viewer module"
  !insertmacro MUI_DESCRIPTION_TEXT ${SEC_MOD_12} "Install plot_gui module"
  !insertmacro MUI_DESCRIPTION_TEXT ${SEC_MOD_13} "Install py_gui_runner module"
  !insertmacro MUI_DESCRIPTION_TEXT ${SEC_MOD_14} "Install recipe_wheel module"
  !insertmacro MUI_DESCRIPTION_TEXT ${SEC_MOD_15} "Install report module"
  !insertmacro MUI_DESCRIPTION_TEXT ${SEC_MOD_16} "Install split_para module"
  !insertmacro MUI_DESCRIPTION_TEXT ${SEC_MOD_17} "Install sudoku_studio module"
  !insertmacro MUI_DESCRIPTION_TEXT ${SEC_MOD_18} "Install system_info module"
  !insertmacro MUI_DESCRIPTION_TEXT ${SEC_MOD_19} "Install template_module module"
  !insertmacro MUI_DESCRIPTION_TEXT ${SEC_MOD_20} "Install todo_list module"
  !insertmacro MUI_DESCRIPTION_TEXT ${SEC_MOD_21} "Install translator module"
  !insertmacro MUI_DESCRIPTION_TEXT ${SEC_MOD_22} "Install unit_converter module"
  !insertmacro MUI_DESCRIPTION_TEXT ${SEC_MOD_23} "Install video module"
  !insertmacro MUI_DESCRIPTION_TEXT ${SEC_MOD_24} "Install youtube_downloader module"
!insertmacro MUI_FUNCTION_DESCRIPTION_END


Function ShowModuleSections
  SectionSetText ${SEC_MOD_0} "Fitter"
  SectionSetText ${SEC_MOD_1} "browser"
  SectionSetText ${SEC_MOD_2} "clock"
  SectionSetText ${SEC_MOD_3} "color_palette"
  SectionSetText ${SEC_MOD_4} "draw"
  SectionSetText ${SEC_MOD_5} "exe_embedder"
  SectionSetText ${SEC_MOD_6} "gui_cmd"
  SectionSetText ${SEC_MOD_7} "image_editor"
  SectionSetText ${SEC_MOD_8} "mp4_processor"
  SectionSetText ${SEC_MOD_9} "notepad"
  SectionSetText ${SEC_MOD_10} "pdf_processor"
  SectionSetText ${SEC_MOD_11} "pdf_viewer"
  SectionSetText ${SEC_MOD_12} "plot_gui"
  SectionSetText ${SEC_MOD_13} "py_gui_runner"
  SectionSetText ${SEC_MOD_14} "recipe_wheel"
  SectionSetText ${SEC_MOD_15} "report"
  SectionSetText ${SEC_MOD_16} "split_para"
  SectionSetText ${SEC_MOD_17} "sudoku_studio"
  SectionSetText ${SEC_MOD_18} "system_info"
  SectionSetText ${SEC_MOD_19} "template_module"
  SectionSetText ${SEC_MOD_20} "todo_list"
  SectionSetText ${SEC_MOD_21} "translator"
  SectionSetText ${SEC_MOD_22} "unit_converter"
  SectionSetText ${SEC_MOD_23} "video"
  SectionSetText ${SEC_MOD_24} "youtube_downloader"
FunctionEnd

Function HideModuleSections
  SectionSetText ${SEC_MOD_0} ""
  SectionSetText ${SEC_MOD_1} ""
  SectionSetText ${SEC_MOD_2} ""
  SectionSetText ${SEC_MOD_3} ""
  SectionSetText ${SEC_MOD_4} ""
  SectionSetText ${SEC_MOD_5} ""
  SectionSetText ${SEC_MOD_6} ""
  SectionSetText ${SEC_MOD_7} ""
  SectionSetText ${SEC_MOD_8} ""
  SectionSetText ${SEC_MOD_9} ""
  SectionSetText ${SEC_MOD_10} ""
  SectionSetText ${SEC_MOD_11} ""
  SectionSetText ${SEC_MOD_12} ""
  SectionSetText ${SEC_MOD_13} ""
  SectionSetText ${SEC_MOD_14} ""
  SectionSetText ${SEC_MOD_15} ""
  SectionSetText ${SEC_MOD_16} ""
  SectionSetText ${SEC_MOD_17} ""
  SectionSetText ${SEC_MOD_18} ""
  SectionSetText ${SEC_MOD_19} ""
  SectionSetText ${SEC_MOD_20} ""
  SectionSetText ${SEC_MOD_21} ""
  SectionSetText ${SEC_MOD_22} ""
  SectionSetText ${SEC_MOD_23} ""
  SectionSetText ${SEC_MOD_24} ""
FunctionEnd

Function InitModuleSelection
  ; Initialize module selection based on existing files in update mode
  ; First unselect all to be safe? The loop handles both 0 and 1 cases.

  ; Check Fitter
  IfFileExists "$INSTDIR\_internal\modules\Fitter.py" 0 +3
    SectionSetFlags ${SEC_MOD_0} 1
    Goto +2
    SectionSetFlags ${SEC_MOD_0} 0


  ; Check browser
  IfFileExists "$INSTDIR\_internal\modules\browser.py" 0 +3
    SectionSetFlags ${SEC_MOD_1} 1
    Goto +2
    SectionSetFlags ${SEC_MOD_1} 0


  ; Check clock
  IfFileExists "$INSTDIR\_internal\modules\clock.py" 0 +3
    SectionSetFlags ${SEC_MOD_2} 1
    Goto +2
    SectionSetFlags ${SEC_MOD_2} 0


  ; Check color_palette
  IfFileExists "$INSTDIR\_internal\modules\color_palette.py" 0 +3
    SectionSetFlags ${SEC_MOD_3} 1
    Goto +2
    SectionSetFlags ${SEC_MOD_3} 0


  ; Check draw
  IfFileExists "$INSTDIR\_internal\modules\draw.py" 0 +3
    SectionSetFlags ${SEC_MOD_4} 1
    Goto +2
    SectionSetFlags ${SEC_MOD_4} 0


  ; Check exe_embedder
  IfFileExists "$INSTDIR\_internal\modules\exe_embedder.py" 0 +3
    SectionSetFlags ${SEC_MOD_5} 1
    Goto +2
    SectionSetFlags ${SEC_MOD_5} 0


  ; Check gui_cmd
  IfFileExists "$INSTDIR\_internal\modules\gui_cmd.py" 0 +3
    SectionSetFlags ${SEC_MOD_6} 1
    Goto +2
    SectionSetFlags ${SEC_MOD_6} 0


  ; Check image_editor
  IfFileExists "$INSTDIR\_internal\modules\image_editor.py" 0 +3
    SectionSetFlags ${SEC_MOD_7} 1
    Goto +2
    SectionSetFlags ${SEC_MOD_7} 0


  ; Check mp4_processor
  IfFileExists "$INSTDIR\_internal\modules\mp4_processor.py" 0 +3
    SectionSetFlags ${SEC_MOD_8} 1
    Goto +2
    SectionSetFlags ${SEC_MOD_8} 0


  ; Check notepad
  IfFileExists "$INSTDIR\_internal\modules\notepad.py" 0 +3
    SectionSetFlags ${SEC_MOD_9} 1
    Goto +2
    SectionSetFlags ${SEC_MOD_9} 0


  ; Check pdf_processor
  IfFileExists "$INSTDIR\_internal\modules\pdf_processor.py" 0 +3
    SectionSetFlags ${SEC_MOD_10} 1
    Goto +2
    SectionSetFlags ${SEC_MOD_10} 0


  ; Check pdf_viewer
  IfFileExists "$INSTDIR\_internal\modules\pdf_viewer.py" 0 +3
    SectionSetFlags ${SEC_MOD_11} 1
    Goto +2
    SectionSetFlags ${SEC_MOD_11} 0


  ; Check plot_gui
  IfFileExists "$INSTDIR\_internal\modules\plot_gui.py" 0 +3
    SectionSetFlags ${SEC_MOD_12} 1
    Goto +2
    SectionSetFlags ${SEC_MOD_12} 0


  ; Check py_gui_runner
  IfFileExists "$INSTDIR\_internal\modules\py_gui_runner.py" 0 +3
    SectionSetFlags ${SEC_MOD_13} 1
    Goto +2
    SectionSetFlags ${SEC_MOD_13} 0


  ; Check recipe_wheel
  IfFileExists "$INSTDIR\_internal\modules\recipe_wheel.py" 0 +3
    SectionSetFlags ${SEC_MOD_14} 1
    Goto +2
    SectionSetFlags ${SEC_MOD_14} 0


  ; Check report
  IfFileExists "$INSTDIR\_internal\modules\report.py" 0 +3
    SectionSetFlags ${SEC_MOD_15} 1
    Goto +2
    SectionSetFlags ${SEC_MOD_15} 0


  ; Check split_para
  IfFileExists "$INSTDIR\_internal\modules\split_para.py" 0 +3
    SectionSetFlags ${SEC_MOD_16} 1
    Goto +2
    SectionSetFlags ${SEC_MOD_16} 0


  ; Check sudoku_studio
  IfFileExists "$INSTDIR\_internal\modules\sudoku_studio.py" 0 +3
    SectionSetFlags ${SEC_MOD_17} 1
    Goto +2
    SectionSetFlags ${SEC_MOD_17} 0


  ; Check system_info
  IfFileExists "$INSTDIR\_internal\modules\system_info.py" 0 +3
    SectionSetFlags ${SEC_MOD_18} 1
    Goto +2
    SectionSetFlags ${SEC_MOD_18} 0


  ; Check template_module
  IfFileExists "$INSTDIR\_internal\modules\template_module.py" 0 +3
    SectionSetFlags ${SEC_MOD_19} 1
    Goto +2
    SectionSetFlags ${SEC_MOD_19} 0


  ; Check todo_list
  IfFileExists "$INSTDIR\_internal\modules\todo_list.py" 0 +3
    SectionSetFlags ${SEC_MOD_20} 1
    Goto +2
    SectionSetFlags ${SEC_MOD_20} 0


  ; Check translator
  IfFileExists "$INSTDIR\_internal\modules\translator.py" 0 +3
    SectionSetFlags ${SEC_MOD_21} 1
    Goto +2
    SectionSetFlags ${SEC_MOD_21} 0


  ; Check unit_converter
  IfFileExists "$INSTDIR\_internal\modules\unit_converter.py" 0 +3
    SectionSetFlags ${SEC_MOD_22} 1
    Goto +2
    SectionSetFlags ${SEC_MOD_22} 0


  ; Check video
  IfFileExists "$INSTDIR\_internal\modules\video.py" 0 +3
    SectionSetFlags ${SEC_MOD_23} 1
    Goto +2
    SectionSetFlags ${SEC_MOD_23} 0


  ; Check youtube_downloader
  IfFileExists "$INSTDIR\_internal\modules\youtube_downloader.py" 0 +3
    SectionSetFlags ${SEC_MOD_24} 1
    Goto +2
    SectionSetFlags ${SEC_MOD_24} 0

FunctionEnd


Function PrePageShortcuts
  ; Hide Modules, Show Shortcuts
  Call HideModuleSections
  SectionSetText ${SEC02} "Desktop Shortcut"
  SectionSetText ${SEC03} "Quick Launch Shortcut"
FunctionEnd

Function PrePageModules
  ; Show Modules, Hide Shortcuts
  Call ShowModuleSections
  SectionSetText ${SEC02} ""
  SectionSetText ${SEC03} ""
FunctionEnd

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

  ; 1. 強制關閉正在運行的程式 (TaskKill)
  ; 嘗試關閉 FlexiTools.exe。/F 強制，/IM 指定映像名稱。
  ; 使用 ExecWait 確保在繼續之前命令執行完畢。
  ; 為了避免使用者混淆，可以使用 Banner 或 DetailPrint (但 .onInit 時還沒介面)，
  ; 或者直接執行，如果沒運行也不會報錯 (會有 error code 但不影響安裝)。
  ExecWait "taskkill /F /IM FlexiTools.exe"

  ; 檢查命令列參數是否包含 /UPDATE
  ${GetOptions} $CMDLINE "/UPDATE" $R0
  IfErrors +3 0
    StrCpy $IsUpdateMode "1"
    ; Note: SetSilent removed/commented out to allow interactive update as requested
    ; SetSilent silent

  ; 檢查是否已安裝
  ReadRegStr $R0 ${PRODUCT_UNINST_ROOT_KEY} "${PRODUCT_UNINST_KEY}" "UninstallString"
  StrCmp $R0 "" first_install

  ; 已安裝，設定為非首次安裝
  StrCpy $IsFirstInstall "0"

  ; 如果是更新模式，我們需要先記錄原本安裝了哪些模組 (InitModuleSelection)
  ; 然後再執行卸載。
  ${If} $IsUpdateMode == "1"
    ; 先偵測並標記模組 (因為卸載後檔案就不見了)
    Call InitModuleSelection

    ; 自動執行舊版卸載程序
    ; 使用 _?=$INSTDIR 參數讓卸載程式在安裝目錄執行但不複製到暫存區，這樣 Wait 才能真正等待它結束
    ; 加上 /S 靜默卸載，避免跳出確認視窗
    DetailPrint "Uninstalling previous version..."
    ExecWait '$R0 /S _?=$INSTDIR'

    ; 卸載完成後，繼續安裝
    Goto done
  ${EndIf}

  ; 手動安裝模式：詢問是否卸載舊版
  MessageBox MB_OKCANCEL|MB_ICONEXCLAMATION \
  "${PRODUCT_NAME} is already installed.$\n$\nClick OK to remove the previous version and install the new one." \
  /SD IDOK IDOK uninst
  Abort

uninst:
  ClearErrors
  ; 手動模式下，先偵測模組狀態以便預設勾選 (User Experience improvement)
  Call InitModuleSelection

  ; 執行卸載 (靜默或非靜默? 通常重裝建議靜默以免麻煩)
  ; 這裡保持使用者確認後的自動卸載
  ExecWait '$R0 /S _?=$INSTDIR'

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
  ; 卸載前也嘗試關閉程式
  ExecWait "taskkill /F /IM FlexiTools.exe"

  ; 如果是靜默模式 (更新時自動調用)，跳過確認
  ${If} ${Silent}
    Return
  ${EndIf}

  MessageBox MB_ICONQUESTION|MB_YESNO|MB_DEFBUTTON2 "Are you sure you want to completely remove ${PRODUCT_NAME} and all of its components?" /SD IDYES IDYES +2
  Abort
FunctionEnd

Function un.onUninstSuccess
  ; 如果是靜默模式，跳過成功訊息
  ${If} ${Silent}
    Return
  ${EndIf}

  HideWindow
  MessageBox MB_ICONINFORMATION|MB_OK "${PRODUCT_NAME} has been successfully removed from your computer." /SD IDOK
FunctionEnd
