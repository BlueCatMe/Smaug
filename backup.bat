@ECHO OFF
SET SCRIPT_PATH=%~dp0
SET SRC=%~1
SET DEST=%~2

if "[%SRC%]"=="[]" (
	echo.
	echo 	%0 src [dest]
	echo. 
	echo 	src: can be file or folder"
	echo 	dest: remote path start by '/' and seperated by '/'. Ex: /upload/new
	exit /b
)

if "[%DEST%]"=="[]" (
	SET DEST="/"
)

SET BACKUP_FOLDER=%SRC%.uploaded
SET UPLOAD_LOG=%SRC%.upload.log

python "%SCRIPT_PATH%\main.py" upload "%SRC%" --remote-folder "%DEST%" --move-to-backup-folder "%BACKUP_FOLDER%" --move-skipped-file --log-file "%UPLOAD_LOG%"
