pkill node
pkill hypercorn
nohup python3 ./plant_tree_db/remove_json.py &
nohup bash run1.sh &
nohup bash run2.sh &
