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
    tree_text character varying
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
ADD COLUMN filename character varying,
ADD COLUMN file_bin bytea;
-- add dating tree marker
ALTER TABLE trees
ADD COLUMN is_dating boolean default false;
-- add date
ALTER TABLE treefile
    ADD COLUMN upload_date date;
ALTER TABLE matrix
    ADD COLUMN upload_date date;
-- add submit user
ALTER TABLE trees
    ADD COLUMN email character varying(255);
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
    
99. query
```postgresql
SELECT DISTINCT node_label, designated_tax_id,  tree_id FROM nodes 
WHERE nodes.designated_tax_id 
IN (SELECT tax_id FROM ncbi_names 
WHERE ncbi_names.name_txt LIKE 'Oryza sativa');
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