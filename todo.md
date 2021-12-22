```mermaid
%%{init: {'theme': 'default'}}%%
gantt
    dateFormat YYYYMMDD
    title Progress

section Design
Design project: done, z1, 20211209, 2d
Use mermaid: done, 20211211, 1d

section Learn background
Read paper: active, a1, 20211210, 2d
Read manual: done, a2, after a1, 2d

section Collect Tree
Download Treebase: done, b1, 20211211, 3d
Import Treebase: done, b2, after b1, 2d
Export Trees: done, b22, after b2, 6d
Download Open tree project: done, b3, 2d
Import Open tree project: active,b4, after b3, 2d
Design database: active, b6, 20211218, 5d
Design taxon table: active, b7, before b6, 3d
Design form: active, b8, after b7, 2d
From paper: active, b5, after b4, 10d

section Backend
Reuse mai_web: active, c1, 20211211, 3d
Study PostgreSQL: active, c2, after c1, 5d
Write simple query website: active, c3, after b2, 1d

section Frontend
Study forester.js:active, d1, 3d
Study drawtree.js:active, d1, 3d
Tree analyze: active, d2, after d1
Tree submit: active, d3, after c1, 2d
```
