#!/bin/bash
pyinstaller --onefile --add-data "static:static" --add-data "templates:templates" --add-data "pkg:pkg" wsgi.py --name \
nodeAgent --distpath ./deploy