# plant_tree_db
Plant phylogenetic tree database

植物系统发育树数据库

# Compare
## TreeBase:
> "TreeBASE is a repository of phylogenetic information, specifically user-submitted phylogenetic trees **and the data used to generate them**. "

> "TreeBASE accepts **all kinds of phylogenetic data** (e.g., trees of species, trees of populations, trees of genes) representing all biotic taxa"

> "Data used in publications that are in preparation or in review can be submitted to TreeBASE but will not be available to the public until they have passed peer review. "

> "As of April 2014, TreeBASE contains data for 4,076 publications written by 8,777 different authors. These studies analyzed 8,233 matrices and resulted in 12,817 trees with 761,460 taxon labels that mapped to 104,593 distinct taxa."

### Features
- Richer annotation of metadata (journal DOIs, specimen georeferences, Genbank accession numbers, etc)

-  A mapping between taxon labels and taxonomic names in uBio and NCBI for improved normalization of names

- The ability to visualize and edit trees using Phylowidget

- The ability to search on tree topology

- Persistent and resolvable URIs for data objects in TreeBASE (i.e. studies, trees, matrices) serve as both globally unique identification numbers and resource locators. These can be included in articles and on researcher's websites, making access to TreeBASE data only a click away

- Data are delivered in several serializations, including NEXUS and NeXML

- A special URL gives journal editors and reviewers anonymous advanced access to data

- Programmatic access to the data using the PhyloWS API.

### Database
```mermaid
flowchart TB
    subgraph Study
        Journal
        Book
        Conference
        Analysis
    end
    subgraph Analysis
        software
        algorithm
        Matrix
        tree
    end
    subgraph Matrix
        input
    end
    subgraph tree
        label
        title
        type --- single
        type --- consensus
        type --- supertree
        kind --- barcode
        kind --- species
        kind --- gene
        quality --- alternative
        quality --- unrated
        quality --- preferred
        quality --- suboptimal
        nodes --> edges
    end
    subgraph edges
        parent --> child
    end
```
![treebase.png](treebase.png)
## Open tree of life: 
> "Finally, TreeBASE, supplemented with data from Dryad served as the core source of data for Open Tree of Life"

>"Up to summer 2015, the release cycle has been months between new versions of the synthetic tree, but this should shorten in the future. "

> drawtree.js (FreeBSD license)

### Features
- 将已发表的树合成为一个大树, [Progress](https://tree.opentreeoflife.org/about/progress)显示已整合87740OTU，还有3855030未整合。
- 数据可下载，为json，使用专有OTT的ID，
- OTT为整合多个分类信息来源的taxonomy系统，包括NCIB, GBIF

# Structure
```mermaid
%%{init: {'theme': 'base'}}%%
flowchart LR
    subgraph 前端
        Query[查询]
        View[浏览]
        Analyze[分析处理]
        Submit[提交]
    end
    subgraph 后端
        Storage[存储]
        Organize[整理/收集/挖掘]
        ID_Generator[分配记录ID]
    end
    前端 <-->|json| 后端
```
```mermaid
%%{init: {'theme': 'base'}}%%
flowchart LR
    subgraph 前端
        subgraph Query
            q1[Taxonomy]
            q1 --- qq1[Scientific name]
            q1 --- qq2[Common name]
            q1 --- qq3[Chinese name]
            q2[Publish date]
            q3[Tree type]
            q3 --- t1(gene tree)
            q3 --- t2(species tree)
            q3 --- t3(morphology tree)
            q3 --- t4(dating tree)
            q4[Topology, resolution, confidence]
        end
        subgraph View
            v1[d3.js]
            v2[forester]
            v3[drawtree.js]
            v4[Other js library]
        end
        subgraph Analyze
            Reroot --> forester
            Transform --> forester
            Collapse --> forester
            Compare --> a1[Other program]
            Statistics --> a1
        end
        subgraph Submit
            s0[Submit data] --- sf1[Normal form]
            s0[Submit data] --- sf2[Auto-fill form]
            s1[Submit analyze] --- sa2[Free Computing Resources]
            s1[Submit analyze] --- sa3[Local Analyze Command] -.- PhyloSuite
            s1[Submit analyze] -.- sa1[先导一号]
        end
    end
```

```mermaid
%%{init: {'theme': 'base'}}%%
flowchart TB
    subgraph 后端
        u[Unique Tree ID] <-.-> t[Unique Taxonomy ID?]
        subgraph Collect
            s1[Other database's API] --> Import
            s2[dyrad, zenodo] --> Import
            s3[Paper] --> Import
            s4[Collaborate Journal] --> Import
            JSE -.- s4
        end
        subgraph Extract
            e1[Topology info]
            e2[Samples info]
        end
        subgraph Database
            db1 --> d2[Paper info]
            db1 --> d3[Researcher info]
            db1 --> d4[tree info]
            db1 --> d5[tree file]
            SQLite --> db1[(PostgreSQL)]
        end
        Collect --> u
        Extract --> u
        Database --> u
    end
```