```mermaid
%%{init: {'theme': 'forest'}}%%
gantt
    dateFormat YYYYMMDD
    title Progress

section Design
Design project: done, z1, 20211209, 2d
Use gantt to manage: milestone, 20211211, 1d

section Collect info
Read paper: active, a1, 20211210, 2d
Read manual: active, a2, after a1, 1d

section Collect Tree
Treebase: crit, active, b1, 20211211, 3d
Open tree project: active, b2, after b1, 2d
From paper: active, b3, after b2, 10d

section Backend
Reuse mai_web: active, c1, 20211211, 3d

section Frontend
JS library for tree:active, d1, 3d
Tree analyze: active, d2, after d1
Tree submit: active, d3, after c1, 2d
```
