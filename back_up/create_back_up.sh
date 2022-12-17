#!/usr/bin/env bash
timestamp=`date +"%Y-%m-%d"`
mongodump --db autisto --out /tmp/$timestamp
tar -czvf /tmp/inventory_$timestamp.tar.gz /tmp/$timestamp
mv /tmp/inventory_$timestamp.tar.gz /root/back_ups/
