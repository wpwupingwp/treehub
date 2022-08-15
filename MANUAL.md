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
    tree_id integer PRIMARY KEY,
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