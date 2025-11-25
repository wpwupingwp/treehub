#!/bin/bash
pkill node
pkill hypercorn
python3 /home/vms240301/plant_tree_db/remove_json.py
nohup bash /home/vms240301/plant_tree_db/run1.sh &
nohup bash /home/vms240301/plant_tree_db/run2.sh &
