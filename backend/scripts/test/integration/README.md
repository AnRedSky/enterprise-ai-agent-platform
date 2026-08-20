# Frontend / Backend Integration Gate

`01_frontend_backend_gate.ps1` 是唯一自动化联调入口。

强制顺序：Backend regression → migration head → Real API Gate → Frontend test/build → 浏览器联调。
