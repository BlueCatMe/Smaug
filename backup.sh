
SCRIPT_PATH=`dirname $0`
SRC=$1
DEST=$2

if [ "$SRC" = "" ]; then
	echo ""
	echo "	$0 src [dest]"
	echo ""
	echo "	src: can be file or folder"
	echo "	dest: remote path start by '/' and seperated by '/'. Ex: /upload/new"
	echo ""
	exit
fi

if [ "$DEST" = "" ]; then
	DEST='/'
fi

BACKUP_FOLDER=$SRC.uploaded
UPLOAD_LOG=$SRC.upload.log

python "$SCRIPT_PATH/main.py" "$SRC" --remote-folder "$DEST" --move-to-backup-folder "$BACKUP_FOLDER" --move-skipped-file --log-file "$UPLOAD_LOG"
