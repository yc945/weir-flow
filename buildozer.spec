[app]

title = 堰流过流计算
package.name = weirflow
package.domain = org.water.weir

source.dir = .
source.include_exts = py,kv,ttf,otf,png,jpg
# 如有 fonts/CJK.ttf 则自动包含

version = 1.0

# python3 不固定版本，让 Docker 镜像内置 Python 决定（kivy/buildozer 使用 Python 3.11）
requirements = python3,kivy==2.3.0,pillow

# Pin p4a to 2023-09 release: uses Python 3.11 for Android, compatible with
# kivy 2.3.0 Cython C code. p4a master (default) uses Python 3.13/3.14 whose
# removed internal APIs (_PyUnicode_FastCopyCharacters etc.) break kivy 2.3.0.
p4a.branch = 2023.09.16

orientation = portrait
fullscreen = 0

# 图标与启动图（可选）
# presplash.filename = %(source.dir)s/splash.png
# icon.filename      = %(source.dir)s/icon.png

[app:android]

android.api    = 33
android.minapi = 21
android.ndk    = 23b

android.accept_sdk_license = True
android.archs = arm64-v8a

android.permissions =
android.logcat_filters = *:S python:D

[buildozer]
log_level = 2
warn_on_root = 1
