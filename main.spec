# -*- mode: python ; coding: utf-8 -*-

import os
from PyInstaller.utils.hooks import collect_submodules, collect_data_files, collect_dynamic_libs

# OpenCV
cv2_hiddenimports = collect_submodules('cv2')
cv2_datas = collect_data_files('cv2', include_py_files=True)
cv2_binaries = collect_dynamic_libs('cv2')

block_cipher = None

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[
        # CEF 動態函式庫
        ('dependencies/cef_dependencies/subprocess.exe', '.'),
        ('dependencies/cef_dependencies/libcef.dll', '.'),
        ('dependencies/cef_dependencies/d3dcompiler_47.dll', '.'),
        ('dependencies/cef_dependencies/libEGL.dll', '.'),
        ('dependencies/cef_dependencies/libGLESv2.dll', '.'),
        ('dependencies/cef_dependencies/chrome_elf.dll', '.'),
        # OpenCV .pyd/.dll
        *cv2_binaries,
    ],
    datas=[
        ('LICENSE', '.'),
        ("tools.ico", "."),
        # 模組資料與 CEF 資料
        ('modules', 'modules'),
        ('dependencies/cef_dependencies/locales', 'locales'),
        ('dependencies/cef_dependencies/cef.pak', '.'),
        ('dependencies/cef_dependencies/cef_100_percent.pak', '.'),
        ('dependencies/cef_dependencies/cef_200_percent.pak', '.'),
        ('dependencies/cef_dependencies/cef_extensions.pak', '.'),
        ('dependencies/cef_dependencies/devtools_resources.pak', '.'),
        ('dependencies/cef_dependencies/natives_blob.bin', '.'),
        ('dependencies/cef_dependencies/v8_context_snapshot.bin', '.'),
        ('dependencies/cef_dependencies/snapshot_blob.bin', '.'),
        ('dependencies/cef_dependencies/icudtl.dat', '.'),
        ('dependencies/cef_dependencies/MSVCP90.dll', '.'),
        ('dependencies/cef_dependencies/MSVCP100.dll', '.'),
        ('dependencies/ffmpeg/ffmpeg.exe', '.'),  # 確保這路徑正確
        ('dependencies/ffmpeg/avcodec-58.dll', '.'),
        ('dependencies/ffmpeg/avdevice-58.dll', '.'),
        ('dependencies/ffmpeg/avfilter-7.dll', '.'),
        ('dependencies/ffmpeg/avformat-58.dll', '.'),
        ('dependencies/ffmpeg/avutil-56.dll', '.'),
        ('dependencies/ffmpeg/postproc-55.dll', '.'),
        ('dependencies/ffmpeg/swresample-3.dll', '.'),
        ('dependencies/ffmpeg/swscale-5.dll', '.'),
        # OpenCV 資料
        *cv2_datas,
    ],
    hiddenimports=[
        # OpenCV 隱藏模組
        *cv2_hiddenimports,

        # GUI 與 tkinter 模組
        'tkinter',
        'tkinter.filedialog',
        'tkinter.colorchooser',
        'tkinter.simpledialog',
        'tkinter.scrolledtext',

        # 圖片處理
        'PIL',
        'PIL.Image',
        'PIL.ImageTk',
        'PIL.ImageDraw',
        'PIL.ImageFont',

        # 資料處理
        'pandas',
        'openpyxl',
        'psutil',
        'lmfit',
        'numpy',

        # PDF 相關
        'PyPDF2',
        'pdfrw',
        'reportlab',
        'reportlab.pdfgen',
        'reportlab.platypus',
        'reportlab.lib.colors',
        'reportlab.graphics.shapes',
        'reportlab.graphics.charts',
        'reportlab.graphics.widgets.markers',

        # 影片與音訊
        'moviepy',
        'moviepy.editor',
        'moviepy.video.io.ffmpeg_reader',
        'moviepy.video.io.ffmpeg_tools',
        'moviepy.audio.io.AudioFileClip',
        'moviepy.video.fx.all',

        # 視窗系統
        'cefpython3',
        'win32gui',
        'win32con',
        'win32api',
        'pywintypes',
        'win32process',

        # 背景去除（rembg）
        'rembg',
        'rembg.bg',
        'rembg.session_factory',
        'rembg.commands',
        'onnxruntime',

        # 其他潛在隱藏模組
        'pkg_resources.py2_warn',
        'fitz',
        'scipy','scipy.io', 'scipy.io.matlab','scipy.signal',
        'yt_dlp',
        'wave','threading','concurrent.futures','multiprocessing','queue','shutil','tempfile','io', 'pygame',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['PyQt5', 'PyQt6', 'PySide6', 'PySide2'],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='FlexiTools',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='tools.ico',
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='FlexiTools',
)


def remove_cef_dlls():
    target_dir = os.path.join("dist", "FlexiTools", "_internal", "cefpython3")
    if not os.path.exists(target_dir):
        return
    dlls_to_delete = [
        "chrome_elf.dll",
        "libcef.dll",
        "MSVCP90.dll",
        "MSVCP100.dll",
        "MSVCP140.dll"
    ]
    for dll in dlls_to_delete:
        try:
            os.remove(os.path.join(target_dir, dll))
            print(f"Removed: {dll}")
        except FileNotFoundError:
            pass

remove_cef_dlls()