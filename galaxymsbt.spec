# -*- mode: python ; coding: utf-8 -*-


block_cipher = None


a = Analysis(
    ['galaxymsbt.py'],
    pathex=['./venv/Lib/site-packages'],
    binaries=[],
    datas=[
        ('assets/dialog_intvar.ui', 'assets'),
        ('assets/dialog_picture.ui', 'assets'),
        ('assets/dialog_ruby.ui', 'assets'),
        ('assets/dialog_stringvar.ui', 'assets'),
        ('assets/dialog_text.ui', 'assets'),
        ('assets/editor.ui', 'assets'),
        ('assets/icon.ico', 'assets'),
        ('assets/tag_delay.png', 'assets'),
        ('assets/tag_format_number.png', 'assets'),
        ('assets/tag_format_string.png', 'assets'),
        ('assets/tag_number_font.png', 'assets'),
        ('assets/tag_page_break.png', 'assets'),
        ('assets/tag_page_center.png', 'assets'),
        ('assets/tag_page_offset.png', 'assets'),
        ('assets/tag_picture.png', 'assets'),
        ('assets/tag_player.png', 'assets'),
        ('assets/tag_race_time.png', 'assets'),
        ('assets/tag_reset_color.png', 'assets'),
        ('assets/tag_ruby.png', 'assets'),
        ('assets/tag_sound.png', 'assets'),
        ('assets/tag_text_color.png', 'assets'),
        ('assets/tag_text_size.png', 'assets'),
    ],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

# https://stackoverflow.com/questions/58097858/how-to-exclude-opengl32sw-dll-from-pyqt5-library-when-using-pyinstaller
to_keep = []
to_exclude = {
    "Qt5Qml.dll",
    "Qt5QmlModels.dll",
    "Qt5WebSockets.dll",
    "Qt5Network.dll",
    "Qt5Quick.dll",
    "Qt5Svg.dll",
    "Qt5DBus.dll",
    "opengl32sw.dll",
    "d3dcompiler_47.dll",
}

# Iterate through the list of included binaries.
for (dest, source, kind) in a.binaries:
    # Skip anything we don't need.
    if os.path.split(dest)[1] in to_exclude:
        continue
    to_keep.append((dest, source, kind))

# Replace list of data files with filtered one.
a.binaries = to_keep

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='galaxymsbt',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
	icon='assets/icon.ico',
)
