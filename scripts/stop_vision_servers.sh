#!/usr/bin/env bash
# Stop the three vision-expert gradio servers started by start_vision_servers.sh.
pkill -f "python som_server.py" && echo "stopped SOM" || echo "SOM not running"
pkill -f "python grounding_dino_server.py" && echo "stopped GroundingDINO" || echo "GroundingDINO not running"
pkill -f "python depthanything_server.py" && echo "stopped Depth-Anything" || echo "Depth-Anything not running"
