# plant_tree_db
Plant phylogenetic tree database

植物系统发育树数据库

# Structure
```mermaid
graph plant_tree_db
    subgraph front
        View
        Analyze
    end
    subgraph end
        Storage
    end
    front <-> end
```