#!/bin/bash
ps -ef | grep python |grep src/main.py | awk '{print $2}' |xargs -i kill -9 {}