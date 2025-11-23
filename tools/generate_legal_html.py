import json
import datetime

def generate_html():
    with open('licenses_pypi.json', 'r', encoding='utf-8') as f:
        licenses = json.load(f)

    # Sort by name
    licenses.sort(key=lambda x: x['Name'].lower())

    html_content = f"""<!DOCTYPE html>
<html lang="zh-TW">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>法律聲明與開源授權 - FlexiTools</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css">
    <style>
        body {{
            background: radial-gradient(circle at center, #1b2735 0%, #090a0f 100%);
            color: #e0e0e0;
            font-family: 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
            min-height: 100vh;
        }}

        .glass-panel {{
            background: rgba(255, 255, 255, 0.05);
            backdrop-filter: blur(10px);
            border: 1px solid rgba(255, 255, 255, 0.1);
            border-radius: 15px;
            padding: 20px;
            margin-bottom: 20px;
        }}

        .glass-header {{
            background: rgba(0, 0, 0, 0.2);
            backdrop-filter: blur(15px);
            border-bottom: 1px solid rgba(255, 255, 255, 0.05);
            position: sticky;
            top: 0;
            z-index: 1000;
        }}

        h1, h2, h3 {{
            color: #fff;
            font-weight: 300;
        }}

        a {{
            color: #4db8ff;
            text-decoration: none;
            transition: color 0.3s;
        }}

        a:hover {{
            color: #80d4ff;
            text-decoration: underline;
        }}

        .license-card {{
            transition: transform 0.2s, background 0.2s;
        }}

        .license-card:hover {{
            background: rgba(255, 255, 255, 0.08);
            transform: translateY(-2px);
        }}

        .badge-license {{
            background: rgba(77, 184, 255, 0.2);
            color: #80d4ff;
            border: 1px solid rgba(77, 184, 255, 0.3);
        }}

        .badge-version {{
            background: rgba(255, 255, 255, 0.1);
            color: #ccc;
        }}

        .search-box {{
            background: rgba(0, 0, 0, 0.2);
            border: 1px solid rgba(255, 255, 255, 0.1);
            color: #fff;
        }}

        .search-box:focus {{
            background: rgba(0, 0, 0, 0.3);
            border-color: #4db8ff;
            color: #fff;
            box-shadow: 0 0 10px rgba(77, 184, 255, 0.2);
        }}

        /* Scrollbar */
        ::-webkit-scrollbar {{
            width: 10px;
        }}
        ::-webkit-scrollbar-track {{
            background: #090a0f;
        }}
        ::-webkit-scrollbar-thumb {{
            background: #333;
            border-radius: 5px;
        }}
        ::-webkit-scrollbar-thumb:hover {{
            background: #555;
        }}
    </style>
</head>
<body>

    <!-- Navigation -->
    <nav class="navbar navbar-expand-lg navbar-dark glass-header mb-4">
        <div class="container">
            <a class="navbar-brand" href="index.html">
                <i class="fas fa-tools me-2"></i>FlexiTools
            </a>
            <span class="navbar-text text-white-50 ms-3 border-start ps-3">
                法律聲明與開源授權
            </span>
        </div>
    </nav>

    <div class="container">
        <div class="row mb-5">
            <div class="col-12 text-center">
                <h1 class="display-4 mb-3">開源授權聲明</h1>
                <p class="lead text-white-50">
                    FlexiTools 是基於多個優秀的開源專案構建的。我們誠摯地感謝這些開發者與社群的貢獻。
                    <br>
                    本專案本身採用 <strong class="text-white">AGPLv3</strong> 授權。
                </p>
                <p class="text-muted small">
                    最後更新時間: {datetime.datetime.now().strftime('%Y-%m-%d')}
                </p>
            </div>
        </div>

        <!-- Search -->
        <div class="row mb-4 justify-content-center">
            <div class="col-md-6">
                <input type="text" id="searchInput" class="form-control search-box form-control-lg text-center" placeholder="搜尋套件或授權...">
            </div>
        </div>

        <!-- Project License -->
        <div class="glass-panel mb-5">
            <h2 class="border-bottom border-secondary pb-2 mb-3">
                <i class="fas fa-balance-scale me-2"></i>FlexiTools 授權
            </h2>
            <p>
                <strong>FlexiTools</strong> 原始碼採用 <strong>GNU Affero General Public License v3.0 (AGPL-3.0)</strong> 授權。
                這意味著如果您修改並發布此軟體（或通過網路提供服務），您必須以相同的授權條款公開您的修改內容。
            </p>
            <div class="mt-3">
                <a href="https://www.gnu.org/licenses/agpl-3.0.html" target="_blank" class="btn btn-outline-light btn-sm">
                    <i class="fas fa-external-link-alt me-1"></i>閱讀 AGPLv3 全文
                </a>
            </div>
        </div>

        <!-- Dependencies List -->
        <h2 class="mb-4"><i class="fas fa-cubes me-2"></i>第三方相依套件</h2>

        <div class="row" id="licenseGrid">
"""

    for pkg in licenses:
        name = pkg.get('Name', 'Unknown')
        version = pkg.get('Version', 'Unknown')
        license_name = pkg.get('License', 'Unknown')
        url = pkg.get('URL', '#')
        summary = pkg.get('Summary', 'No description available.')

        # Shorten summary
        if summary and len(summary) > 100:
            summary = summary[:97] + "..."

        html_content += f"""
            <div class="col-md-6 col-lg-4 mb-4 license-item">
                <div class="glass-panel h-100 license-card d-flex flex-column">
                    <div class="d-flex justify-content-between align-items-start mb-2">
                        <h5 class="mb-0 text-break">{name}</h5>
                        <span class="badge badge-version">{version}</span>
                    </div>
                    <div class="mb-2">
                        <span class="badge badge-license">{license_name}</span>
                    </div>
                    <p class="small text-white-50 flex-grow-1">{summary}</p>
                    <div class="mt-auto pt-3 border-top border-secondary w-100">
                        <a href="{url}" target="_blank" class="small text-decoration-none">
                            <i class="fas fa-link me-1"></i>官方網站 / 原始碼
                        </a>
                    </div>
                </div>
            </div>
"""

    html_content += """
        </div>

        <div class="text-center mt-5 mb-5 text-white-50 small">
            <p>本頁面由自動化工具生成。若發現資訊有誤，請提交 Issue。</p>
        </div>
    </div>

    <script>
        document.getElementById('searchInput').addEventListener('keyup', function(e) {
            const term = e.target.value.toLowerCase();
            const items = document.querySelectorAll('.license-item');

            items.forEach(item => {
                const text = item.textContent.toLowerCase();
                if(text.includes(term)) {
                    item.style.display = 'block';
                } else {
                    item.style.display = 'none';
                }
            });
        });
    </script>
</body>
</html>
"""

    with open('docs/LEGAL.html', 'w', encoding='utf-8') as f:
        f.write(html_content)

    print("Generated docs/LEGAL.html")

if __name__ == "__main__":
    generate_html()
