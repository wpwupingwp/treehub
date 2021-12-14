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
Read manual: active, a2, after a1, 2d

section Collect Tree
Download Treebase: done, b1, 20211211, 3d
Import Treebase: done, b2, after b1, 2d
Download Open tree project: done, b3, 2d
Import Open tree project: active,b4, after b3, 2d
From paper: active, b5, after b4, 10d

section Backend
Reuse mai_web: active, c1, 20211211, 3d
Study PostgreSQL: active, c2, after c1, 3d
Write simple query website: active, c3, after b2, 1d

section Frontend
Study forester.js:active, d1, 3d
Study drawtree.js:active, d1, 3d
Tree analyze: active, d2, after d1
Tree submit: active, d3, after c1, 2d
```
