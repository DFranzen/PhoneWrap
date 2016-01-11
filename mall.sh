DIR=""
POLICY=""
CREATION=""
MARK=""

while [[ $# > 1 ]]
do
key="$1"

case $key in
    -p)
	POLICY="$2"
	echo "policy specified at $POLICY"
    shift # past argument
    ;;
    -c)
	CREATION="true"
    ;;
    -m)
	MARK="true"
    ;;
    *)
	if [[ $DIR="" ]]
	then 
	    DIR=$1
	else
	    >&2 echo "$DIR specified without parameter key"
	    exit 1
	fi 
            # unknown option
    ;;
esac
shift # past argument or value
done
    

./m10_unpack.sh $1
wait
echo "++++++++++++++++++++++++++++++++++++++++"
PARAM=""
if [[ -n $POLICY ]]
then
    PARAM="$PARAM -p $POLICY"
fi
if [[ -n $CREATION ]]
then
    PARAM="$PARAM -c"
fi 
if [[ -n $MARK ]]
then
    PARAM="$PARAM -m"
fi 
./m30_policify.py $PARAM $1.dir
wait
./m90_pack_install.sh $1.dir
