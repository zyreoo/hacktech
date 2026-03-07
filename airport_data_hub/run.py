#!/usr/bin/env python3
"""
Run the Data Hub API. Use this when you're inside airport_data_hub or want a single command.

  From repo root:   python airport_data_hub/run.py
  From this folder: python run.py

Adds project root to sys.path and runs uvicorn with airport_data_hub.main:app so relative imports work.
"""
import os
import sys

# Project root = parent of airport_data_hub
_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _root not in sys.path:
    sys.path.insert(0, _root)

import uvicorn

port = int(os.environ.get("PORT", 8000))
uvicorn.run("airport_data_hub.main:app", host="0.0.0.0", port=port, reload=True)
