[app]

title = 堰流过流计算
package.name = weirflow
package.domain = org.water.weir

source.dir = .
source.include_exts = py,kv,ttf,otf,png,jpg
# 如有 fonts/CJK.ttf 则自动包含

version = 1.0

requirements = python3==3.11.0,kivy==2.3.0,pillow

orientation = portrait
fullscreen = 0

# 图标与启动图（可选）
# presplash.filename = %(source.dir)s/splash.png
# icon.filename      = %(source.dir)s/icon.png

[app:android]

android.api    = 33
android.minapi = 21
android.ndk    = 25b

android.accept_sdk_license = True
android.archs = arm64-v8a

android.permissions =
android.logcat_filters = *:S python:D

[buildozer]
log_level = 2
warn_on_root = 1
