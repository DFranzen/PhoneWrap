path=$1
if [ ${path:(-1)} == "/" ]; then path=${path:0:(-1)}; fi  #remove trailing slash if given
echo "Packaging application with the root dir $path"				 

pkgname="$(basename "$path")"
extension="${pkgname##*.}"
if [ $extension == "dir" ]; then pkgname="${pkgname%.*}"; fi  #remove .dir if given

echo " -> building $path to $path.redist/$pkgname" 

apktool build $path -o $path.redist/$pkgname;
echo " -- signing apk --"
jarsigner -sigalg SHA1withRSA -digestalg SHA1 -keystore my-release-key.keystore -storepass merandroidlin $path.redist/$pkgname alias_name;

echo " -> installing $path.redist/$pkgname"

adb install -r $path.redist/$pkgname
adb-run.sh $path.redist/$pkgname
