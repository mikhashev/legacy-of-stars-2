"""
Test package for Legacy of Stars.

Run everything with:
    python -m unittest discover -s tests -t . -v

Tests never talk to an LLM (LOS_OFFLINE=1) and never write log files.
"""
import logging
import os

os.environ.setdefault("LOS_OFFLINE", "1")
logging.getLogger().addHandler(logging.NullHandler())
