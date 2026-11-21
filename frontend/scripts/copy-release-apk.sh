#!/usr/bin/env sh
set -eu
src="${1:?Pass downloaded EAS APK path}"
test -f "$src"
cp "$src" Aplikasi_Release.apk
printf 'Copied verified build to %s\n' "$(pwd)/Aplikasi_Release.apk"
