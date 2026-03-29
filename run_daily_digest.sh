#!/bin/bash

# Change to the project directory
cd /Users/likaiwen/Desktop/daily_digest

# Activate the virtual environment
source .venv/bin/activate

# Run the Python script
python main.py

# Log the execution
echo "$(date): Script executed" >> /tmp/daily_digest_calendar_run.log