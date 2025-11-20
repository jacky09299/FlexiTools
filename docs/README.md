# FlexiTools UML 文件

這個目錄包含了 FlexiTools 專案的 UML 架構圖生成工具。

## 如何查看架構圖

由於瀏覽器的安全性限制 (CORS)，HTML 網頁無法直接讀取本機的 JSON 檔案 (`file://` 協定)。您需要啟動一個簡易的本地網頁伺服器來查看圖表。

### 方法 1: 使用 Python (推薦)

如果您已安裝 Python，請在專案根目錄開啟終端機 (Terminal / CMD)，然後執行以下指令：

```bash
python -m http.server 8000
```

然後在瀏覽器網址列輸入：
[http://localhost:8000/docs/uml.html](http://localhost:8000/docs/uml.html)

### 方法 2: 使用 VS Code Live Server

如果您使用 Visual Studio Code，可以安裝 "Live Server" 擴充套件。
1. 在 VS Code 中開啟 `docs/uml.html`。
2. 點擊右下角的 "Go Live" 按鈕。

## 如何更新架構圖

本架構圖是**資料驅動 (Data-Driven)** 的。若要修改圖表內容 (例如新增類別、修改關聯)，您不需要修改 HTML 或 JavaScript 程式碼。

只需編輯 `docs/uml_data.json` 檔案即可：

*   **classes**: 定義類別節點。
*   **relationships**: 定義連線 (繼承 `inheritance` 或關聯 `association`)。

網頁重新整理後，圖表會自動重新計算排版並顯示最新的結構。
