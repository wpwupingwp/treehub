cd /home/vms240301/plant_tree_db && source .venv/bin/activate && hypercorn --log-level debug --reload -w 4 web:app -b 0.0.0.0:2022
