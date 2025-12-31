#!/usr/bin/env python3
import importlib, sys, traceback

modules = ["markdown", "MySQLdb", "app", "os"]
failed = []
for m in modules:
    try:
        importlib.import_module(m)
        print(f"OK: {m}")
    except Exception:
        print(f"FAIL: {m}")
        traceback.print_exc()
        failed.append(m)

if failed:
    print("Some imports failed:", failed)
    sys.exit(2)
else:
    print("All imports succeeded")
