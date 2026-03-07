#!/usr/bin/env python3
"""Run the single server (Data Hub + arrival delay prediction) from repo root: python run_hub.py"""
import uvicorn
uvicorn.run("airport_data_hub.main:app", host="127.0.0.1", port=8090, reload=False)
