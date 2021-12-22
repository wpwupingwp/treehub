-- psql -U root -d treebasedmp -f sql.file
-- COPY (SELECT tree_id FROM trees) TO 'e:\\linux\plant_tree_db\\tree_id.csv' WITH (format csv, header);
-- tree id list
COPY (SELECT DISTINCT tree_id, root FROM trees ORDER BY tree_id)
TO 'e:\\linux\plant_tree_db\\tree_node_list.csv'
WITH (format csv, header, encoding 'UTF8', delimiter ';');
-- trees
COPY (SELECT DISTINCT * FROM trees ORDER BY tree_id)
TO 'e:\\linux\plant_tree_db\\trees.csv'
WITH (format csv, header, encoding 'UTF8', delimiter ';');
-- analysis
COPY (SELECT DISTINCT analysis.analysisstep_id AS analysis_id, study_id,
software, algorithm, tree_id
FROM analysis LEFT JOIN analysis_tree
ON analysis.analysisstep_id=analysis_tree.analysisstep_id
ORDER BY analysis.analysisstep_id) TO 'e:\\linux\plant_tree_db\\analysis.csv'
WITH (format csv, header, encoding 'UTF8', delimiter ';');
-- matrix
COPY (SELECT DISTINCT * FROM matrix ORDER BY matrix_id)
TO 'e:\\linux\plant_tree_db\\matrix.csv'
WITH (format csv, header, encoding 'UTF8', delimiter ';');
-- study
COPY (SELECT DISTINCT * FROM study ORDER BY study_id)
TO 'e:\\linux\plant_tree_db\\study.csv'
WITH (format csv, header, encoding 'UTF8', delimiter ';');
-- nodes
COPY (SELECT DISTINCT * FROM nodes ORDER BY node_id)
TO 'e:\\linux\plant_tree_db\\node.csv'
WITH (format csv, header, encoding 'UTF8', delimiter ';');
-- taxon
COPY (SELECT DISTINCT * FROM taxon ORDER BY taxon_id)
TO 'e:\\linux\plant_tree_db\\taxon_id.csv'
WITH (format csv, header, encoding 'UTF8', delimiter ';');
--select distinct *  from study left join analysis on
--study.study_id=analysis.study_id  left join analysis_tree
--on analysis.analysisstep_id=analysis_tree.analysisstep_id left join matrix on
--analysis.analysisstep_id=matrix.analysisstep_id
--order by analysis.analysisstep_id ;
