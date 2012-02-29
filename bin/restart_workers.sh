#!/bin/bash

PYDIR=`which python`
DEPLOYDIR=$1
NUMWORKERS=$2
if [ ! $2 ]
then
        NUMWORKERS=1
fi

echo "Shutting down beanstalk workers: "$DEPLOYDIR;
while :
do
        ps -aef | grep '^[^grep].*'$DEPLOYDIR'.*beanstalk_worker' | awk '{print $2}' > pids.txt
        fileName="pids.txt"
        exec<$fileName
        count=0
        while read line
        do
                count=`expr $count + 1`
        done
        if [ "$count" = 0 ]
        then
                echo "All workers shut down."
                break
        fi
        
        echo $count" workers running... shutting down."
        sudo -u www-data $PYDIR $DEPLOYDIR"manage.py" beanstalk_worker --shutdown
        sleep 2
done
    
echo "Starting "$NUMWORKERS" beanstalk worker(s).."
for i in $(eval echo {1..$NUMWORKERS})
do
        sudo -u www-data $PYDIR $DEPLOYDIR"manage.py" beanstalk_worker --start  & > /dev/null
done
rm pids.txt
