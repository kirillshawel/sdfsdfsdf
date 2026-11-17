[app]
title = mishabetmen
package.name = mishabetmen
package.domain = com.mishabetmen
source.dir = .
source.include_exts = py,png,jpg,kv,atlas,json
version = 1.0.0
requirements = python3,kivy,cryptography,openssl,pysha3
orientation = portrait
fullscreen = 0
android.permissions = INTERNET,WRITE_EXTERNAL_STORAGE,READ_EXTERNAL_STORAGE
android.api = 34
android.minapi = 26
android.ndk = 25b
android.accept_sdk_license = True
android.archs = arm64-v8a
android.allow_backup = True
private.storage = True

[buildozer]
log_level = 2
warn_on_root = 0
