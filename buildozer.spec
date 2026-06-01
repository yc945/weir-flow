[app]

title = 堰流过流计算
package.name = weirflow
package.domain = org.water.weir

source.dir = .
source.include_exts = py,kv,ttf,otf,png,jpg

version = 1.0

# Pin both python3 and hostpython3 to 3.11.0 so p4a version check passes
# (p4a checks python3.version == hostpython3.version).
# kivy 2.3.0 Cython C code is compatible with Python 3.11 but NOT 3.13/3.14.
requirements = python3==3.11.0,hostpython3==3.11.0,kivy==2.3.0,pillow

orientation = portrait
fullscreen = 0

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
