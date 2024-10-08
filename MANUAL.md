# Manual for plant tree database
## Import treebase
0. Install  dependencies.
   - `Python 3` 
   - and `Perl`. For `Windows`, install *Strawberry Perl*.
   - perl module 
        ```powershell
        cpan -i Bio::Phylo::Factory
        ```

1. Download dump file from 
https://figshare.com/articles/dataset/TreeBASEdmp-2019-06-10/8247494 (2019.6)
2. Install `PostgreSQL` and `pgAdmin v6`
3. Created database using the default template 
```postgresql
CREATE DATABASE treebasedmp WITH TEMPLATE = template1;
```
4. Login in
```powershell
psql -d treebasedmp -U root
# enter password
```
5. Execute the SQL dump `Backup.sql`,  using up about 9.5GB of disk space
```postgresql
\i Backup.sql
```
6. Test if import ok
```postgresql
SELECT * FROM trees LIMIT 5;
```
and make sure encoding is utf-8
```postgresql
-- show database info
\l
```
7. Export tree node list and quit `PostgreSQL`
```postgresql
\i export.sql
-- quit
\q
```
8. Export trees
```powershell
chcp 65001
python3 export_tree.py tree_node_list.csv trees
# find . -size 0 -exec echo {} >> empty.list \;
# for i in `cat empty.list`;do mv $i empty/ ; done
rm trees/*.log
```
9. Rename database  (start editing)
```postgresql
ALTER DATABASE treebasedmp RENAME TO treedb;
```
10. Create new table
```postgresql
-- switch to new database
\c treedb
-- show tables
\dt
CREATE TABLE treefile 
(
    treefile_id serial PRIMARY KEY,
    tree_id integer REFERENCES trees(tree_id),
    upload_date date,
    nexus character varying,
    newick character varying,
    phyloxml character varying
);
```
11. Insert data into table
```powershell
python3 import_treefiles.py
```
then validate
```postgresql
SELECT count(*) FROM treefile;
SELECT * FROM treefile;
```
12. add columns 
```postgresql
-- add matrix file
ALTER TABLE matrix
ADD COLUMN fasta character varying;
-- add dating tree marker
ALTER TABLE trees
ADD COLUMN tree_type_new character varying(50);
-- add date
ALTER TABLE matrix
    ADD COLUMN upload_date date;
ALTER TABLE trees
    ADD COLUMN upload_date date;
ALTER TABLE study 
    RENAME COLUMN lastmodifieddate TO upload_date;
-- add submit user
ALTER TABLE trees
    ADD COLUMN email character varying(255);
-- add cover and news
ALTER TABLE submit
    ADD COLUMN cover_img_name character varying,
    ADD COLUMN cover_img bytea,
    ADD COLUMN news boolean default false;
-- add lineage info
ALTER TABLE ncbi_names
    ADD COLUMN genus_id integer,
    ADD COLUMN family_id integer,
    ADD COLUMN order_id integer;
```
13. add user table
```postgresql
CREATE TABLE users
(
user_id serial PRIMARY KEY,
username character varying(100) UNIQUE,
password character varying(100),
register_date date,
failed_login integer DEFAULT 0
);
INSERT INTO users (user_id, username, password) VALUES (1, 'admin', 'password');
INSERT INTO users (user_id, username, password) VALUES (2, 'guest', 'guest');
```
14. add visit table
```postgresql
CREATE TABLE visits
(
    visit_id bigserial PRIMARY KEY,
    user_id integer REFERENCES users(user_id),
    ip character varying(100),
    url character varying(200),
    useragent character varying(200),
    date date
);
```
15. add submit table
```postgresql
   CREATE TABLE submit
(
    submit_id bigserial PRIMARY KEY,
    email character varying(255),
    ip character varying(100),
    date date,
    user_id integer,
    tree_id integer,
    treefile_id integer,
    study_id integer,
    matrix_id integer 
); 
```
16. add genus, family, order info
```postgresql
COPY (SELECT * FROM ncbi_nodes) TO 'ncbi_nodes' WITH CSV DELIMITER '|' HEADER;
```
```powershell
python3 import_lineage.py
```
```postgresql
CREATE INDEX genus_idx ON ncbi_names (genus_id);
CREATE INDEX family_idx ON ncbi_names (family_id);
CREATE INDEX order_idx ON ncbi_names (order_id)
```
99. query
```postgresql
select * from nodes where nodes.designated_tax_id in
(select tax_id from ncbi_names where ncbi_names.genus_id in 
(SELECT tax_id FROM ncbi_names WHERE ncbi_names.name_txt = 'Oryza'));
-- ambigous search
SELECT DISTINCT node_label, designated_tax_id,  tree_id 
FROM nodes WHERE node_label LIKE 'Oryza sativa%'
```

100. Submit tree
    - nexus or newick tree with raw name
    - {raw name: clean scientific name} table
    - meta info
    - insert into table tree file, tree info, node info
```postgresql
SELECT np.child_path_id AS child_id, ce.parent_id AS parent_id, 
COALESCE( CAST(ce.edge_length AS numeric), 0) AS child_length, ce.edge_support AS child_support, 
cn.node_label AS child_label, COALESCE( CAST(pe.edge_length AS numeric), 0) AS parent_length, 
pe.edge_support AS parent_support, (cn.right_id - cn.left_id) - 1 AS internal
FROM node_path np 
JOIN edges ce ON (np.child_path_id = ce.child_id) 
JOIN nodes cn ON (np.child_path_id = cn.node_id) 
JOIN nodes pn ON (ce.parent_id = pn.node_id) 
LEFT JOIN edges pe ON (pn.node_id = pe.child_id) 
WHERE np.parent_path_id = ?  
STATEMENT
```

200. Install js packages
```powershell
yarn init
yarn add archaeopteryx
# copy required js libraries to node_modules
# edit path in html
#
```
201. Load auspice
```powershell
node auspice.js view --datasetDir plant_tree_db/web/tmp
```

202. Translate
```powershell
# init
cd web
pybabel extract -F babel.cfg -o messages.pot .
pybabel init -i messages.pot -d translations -l zh_CN
# after translate
pybabel compile -d translations
# update
pybabel extract -F babel.cfg -o messages.pot .
pybabel update -i messages.pot -d translations
pybabel compile -d translations
```
203. Backup and restore
```powershell
#backup
# pg_dump -Fd -U root -j 5 -f db_bak2 postgres
pg_dump -U postgres -j 8 -Fd -f db_bak treedb
```
204. Deploy
Install docker
```bash
sudo apt remove docker docker-engine docker.io containerd runc
sudo apt update
sudo apt install ca-certificates curl gnupg lsb-release
sudo mkdir -p /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/debian/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/debian $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
sudo chmod a+r /etc/apt/keyrings/docker.gpg
sudo apt update
sudo apt install docker docker-ce docker-ce-cli containerd.io docker-compose-plugin
sudo docker run hello-world
sudo cat > /etc/docker/daemon.json <<EOF
{
  "registry-mirrors": [
    "https://hub-mirror.c.163.com",
    "https://mirror.baidubce.com"
  ]
}
EOF
```

Install postgresql
```bash
# docker
docker pull postgres:14
# build 
docker build . -t ps_14
docker run --name ps  -p 5432:5432 -v /mnt/e/Linux/plant_tree_db/docker:/tmp -d ps_14 
docker exec -it ps /bin/bash
# run in container
createdb treedb -U postgres
pg_restore -Fd -d treedb db_bak -U postgres -j 8
# export
docker export c7c920 -o ps_14.docker
```
Install nodejs and nginx
```bash
# node js
# install nodejs 16 https://nodejs.org/en/blog/release/v16.16.0/
~/docker/nodejs/nodejs/bin/node auspice.js  view --datasetDir ../plant_tree_db/web/tmp
# gunicorn
sudo apt install nginx gunicorn
sudo cp nginx.txt /etc/nginx/sites-enabled/treedb.conf
nginx -t
sudo systemctl restart nginx
sudo systemctl status nginx
```
Run python
```bash
cd plant_tree_db
pip install -r requirements.txt
gunicorn --worker-class gevent -b 0.0.0.0:9999 -w 4 web:app
# for windows
waitress-serve --listen=127.0.0.1:2022 web:app
```
Backup and restore database
```bash
# edit postgresql.conf
cat << EOF
wal_level = minimal  # requires a restart
maintenance_work_mem = 2GB
max_wal_size = 20GB  # as big as you want
EOF 
# backup
pg_dump -U postgres -F c -f 20240217.sql.bak treedb
# restore
pg_restore -j 8 -U postgres -d treedb .\20240217.sql.bak
```
