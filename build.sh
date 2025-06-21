#!/bin/bash
pyinstaller --onefile --add-data "static:static" --add-data "templates:templates" wsgi.py --name nodeAgent