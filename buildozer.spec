[app]

title = 堰流过流计算
package.name = weirflow
package.domain = org.water.weir

source.dir = .
source.include_exts = py,kv,ttf,otf,ttc,png,jpg

version = 1.0

requirements = python3==3.11.0,hostpython3==3.11.0,kivy==2.3.0,pillow

orientation = portrait
fullscreen = 0

android.api = 33
android.minapi = 21
android.ndk = 25b
android.accept_sdk_license = True
android.archs = arm64-v8a,armeabi-v7a
android.permissions = READ_EXTERNAL_STORAGE,WRITE_EXTERNAL_STORAGE
android.logcat_filters = *:S python:D

p4a.branch = v2024.01.21

[buildozer]
log_level = 2
warn_on_root = 1
