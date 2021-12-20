COPY (SELECT tree_id FROM trees) TO 'e:\\linux\plant_tree_db\\tree_id.csv' WITH (format csv, header);

CREATE VIEW temp AS
SELECT DISTINCT analysis.analysisstep_id AS analysis_id, study_id, software, algorithm, tree_id
FROM analysis LEFT JOIN analysis_tree ON
analysis.analysisstep_id=analysis_tree.analysisstep_id
ORDER BY analysis.analysisstep_id;