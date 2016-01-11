# Script to extract an apk-file
# expected: path to the apk as first argument
# result: unpack the apk into a folder *.apk.dir at the same location

apktool d "$1" -o "$1.dir" > /dev/null
