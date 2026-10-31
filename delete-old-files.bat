@echo off
if exist backend\app\prompts\review_v1.py (del backend\app\prompts\review_v1.py & echo Deleted review_v1.py) else echo review_v1.py already gone
