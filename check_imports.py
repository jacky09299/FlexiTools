import sys
import os

# Add modules to path
sys.path.append(os.getcwd())
sys.path.append(os.path.join(os.getcwd(), "modules"))

# Mock dependencies if missing
try:
    import pandas
except ImportError:
    print("Pandas not found, mocking...")
    sys.modules['pandas'] = type('pandas', (), {})()

try:
    import matplotlib
except ImportError:
    print("Matplotlib not found, mocking...")
    # Create a dummy package for matplotlib
    import types
    mpl = types.ModuleType('matplotlib')
    mpl.use = lambda *a, **k: None
    sys.modules['matplotlib'] = mpl

    mpl_pyplot = types.ModuleType('matplotlib.pyplot')
    mpl_pyplot.subplots = lambda **k: (None, type('Axes', (), {'plot': lambda *a,**k:None, 'set_xlabel': lambda *a:None, 'set_ylabel': lambda *a:None, 'set_title': lambda *a:None, 'legend': lambda *a:None, 'set_xscale': lambda *a:None, 'set_yscale': lambda *a:None, 'grid': lambda *a:None, 'add_subplot': lambda *a:None})())
    mpl_pyplot.figure = lambda **k: type('Figure', (), {'add_subplot': lambda *a: type('Axes', (), {'plot': lambda *a,**k:None, 'axvspan': lambda *a,**k:None, 'text': lambda *a,**k:type('Text',(),{'set_text':lambda x:None, 'set_visible':lambda x:None})(), 'set_xlabel': lambda *a:None, 'set_ylabel': lambda *a:None, 'legend': lambda *a:None, 'set_title': lambda *a:None, 'grid': lambda *a:None})(), 'savefig': lambda *a,**k:None})()
    mpl_pyplot.close = lambda *a: None
    sys.modules['matplotlib.pyplot'] = mpl_pyplot

    mpl_ticker = types.ModuleType('matplotlib.ticker')
    sys.modules['matplotlib.ticker'] = mpl_ticker

    mpl_backend = types.ModuleType('matplotlib.backends')
    sys.modules['matplotlib.backends'] = mpl_backend

    mpl_backend_tkagg = types.ModuleType('matplotlib.backends.backend_tkagg')
    # Mock FigureCanvasTkAgg to return a dummy object with .get_tk_widget().pack()
    class DummyCanvas:
        def __init__(self, *args, **kwargs): pass
        def get_tk_widget(self): return type('Widget', (), {'pack': lambda *a,**k:None, 'grid': lambda *a,**k:None})()
        def draw(self): pass
        def mpl_connect(self, *args): pass
    mpl_backend_tkagg.FigureCanvasTkAgg = DummyCanvas
    sys.modules['matplotlib.backends.backend_tkagg'] = mpl_backend_tkagg

try:
    import cv2
except ImportError:
    sys.modules['cv2'] = type('cv2', (), {})()


try:
    import moviepy.editor
except ImportError:
    sys.modules['moviepy.editor'] = type('editor', (), {'VideoFileClip': type('VideoFileClip', (), {})})()

try:
    import lmfit
except ImportError:
    sys.modules['lmfit'] = type('lmfit', (), {'model': type('model', (), {'Model': type('Model', (), {})}), 'Parameters': type('Parameters', (), {}), 'minimize': lambda *a, **k: None, 'fit_report': lambda *a: ""})()

try:
    import win32gui
except ImportError:
    print("win32gui not found, mocking...")
    sys.modules['win32gui'] = type('win32gui', (), {'GetCursorPos': lambda: (0, 0)})()
    sys.modules['win32api'] = type('win32api', (), {'GetKeyState': lambda x: 0})()
    sys.modules['win32con'] = type('win32con', (), {'VK_LBUTTON': 1})()

try:
    import psutil
except ImportError:
    print("psutil not found, mocking...")
    sys.modules['psutil'] = type('psutil', (), {'cpu_percent': lambda *a, **k: 0, 'virtual_memory': lambda: type('vmem', (), {'percent': 0})()})()

try:
    import numpy
except ImportError:
    sys.modules['numpy'] = type('numpy', (), {})()

try:
    import scipy.signal
except ImportError:
    sys.modules['scipy'] = type('scipy', (), {})()
    sys.modules['scipy.signal'] = type('signal', (), {})()

# Modules to check
modules_to_check = [
    "modules.report",
    "modules.split_para",
    "modules.translator",
    "modules.plot_gui",
    "modules.py_gui_runner",
    "modules.recipe_wheel",
    "modules.sudoku_studio",
    "modules.system_info",
    "modules.todo_list",
    "modules.video",
    "modules.youtube_downloader",
    "modules.Fitter"
]

print("Checking imports...")
for mod in modules_to_check:
    try:
        __import__(mod)
        print(f"Successfully imported {mod}")
    except Exception as e:
        print(f"Failed to import {mod}: {e}")
        sys.exit(1)

print("All modules imported successfully.")
