#!/bin/bash
# =====================================================================
# LAB 6 RANK 1 DEPLOYMENT SCRIPT
# Run this directly on student@10.1.75.53 (stu64_sys1)
# =====================================================================

echo "================================================="
echo "   🚀 DEPLOYING RANK-1 LOAD BALANCER SYSTEM       "
echo "================================================="

# 1. Install required packages
echo "[+] Step 1: Installing dependencies..."
pip install -q fastapi uvicorn[standard] httpx uvloop requests 2>/dev/null || pip3 install fastapi uvicorn httpx uvloop requests

# 2. Check and restart down containers (like sys3 / 172.17.0.16)
echo "[+] Step 2: Checking backend containers..."
if command -v docker &> /dev/null; then
    docker start $(docker ps -a -q) 2>/dev/null || true
fi

# 3. Kill any old process on ports 3000 or 3213
echo "[+] Step 3: Cleaning up old running processes..."
fuser -k 3000/tcp 2>/dev/null || true
fuser -k 3213/tcp 2>/dev/null || true
pkill -f "load_balancer.py" 2>/dev/null || true
pkill -f "uvicorn" 2>/dev/null || true
sleep 1

# 4. Check which port is needed (default is 3000, mapped to host 3213)
PORT=3000
if [ "$1" != "" ]; then
    PORT=$1
fi

echo "[+] Step 4: Starting Ultra-Fast Rank-1 Load Balancer on port $PORT..."
nohup python3 load_balancer.py $PORT > lb.log 2>&1 &
sleep 2

# 5. Local verification
echo "[+] Step 5: Running local health check..."
STATUS=$(curl -s http://127.0.0.1:$PORT/lb/status)
echo "Status response: $STATUS"

echo "================================================="
echo "   ✅ SERVER IS RUNNING IN BACKGROUND!            "
echo "   Log file: tail -f lb.log                       "
echo "================================================="
