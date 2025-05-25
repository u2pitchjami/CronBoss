#!/usr/bin/env python3
from datetime import datetime

now = datetime.now()
with open("test_run.txt", "a") as f:
    f.write(f"Task run at: {now.strftime('%Y-%m-%d %H:%M:%S')}\n")
