#!/bin/bash
#helper bash script to shutdown beanstalk workers nicely and restart a beanstalk worker

PYDIR=`which python`
DEPLOYDIR=$1


echo "Shutting down beanstalk workers";
while :
do
        ps -aef | grep '^[^grep].* beanstalk_worker' | awk '{print $2}' > pids.txt
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

echo "Starting beanstalk workers.."
sudo -u www-data $PYDIR $DEPLOYDIR"manage.py" beanstalk_worker --start  & > /dev/null
rm pids.txt
