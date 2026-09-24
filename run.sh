#!/bin/sh
".venv/bin/python" main.py 2>&1
code=$?
echo "退出码: $code"
exit "$code"