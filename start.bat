@echo off
rem EAP 能力测评一键启动：装依赖 → 起服务 → 打开浏览器
cd /d %~dp0
python -m pip install -r requirements.txt --quiet
start "" http://127.0.0.1:8090
python server.py
