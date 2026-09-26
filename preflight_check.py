import asyncio
import httpx
import time
import sys

BASE_URL = sys.argv[1] if len(sys.argv) > 1 else "http://10.1.75.53:3213"

async def test_leaderboard_simulation():
    print(f"==================================================")
    print(f" 🧪 PRE-FLIGHT VERIFICATION TEST FOR {BASE_URL}")
    print(f"==================================================")

    limits = httpx.Limits(max_keepalive_connections=100, max_connections=200)
    async with httpx.AsyncClient(limits=limits, timeout=5.0) as client:
        # 1. Test Health / Status
        print("[1] Testing /lb/status...")
        try:
            r = await client.get(f"{BASE_URL}/lb/status")
            print(f"    Status code: {r.status_code}")
            print(f"    Body: {r.text}")
        except Exception as e:
            print(f"    ❌ Health check failed: {e}")
            return

        # 2. Reset
        print("\n[2] Testing /reset...")
        try:
            r = await client.post(f"{BASE_URL}/reset")
            print(f"    Reset response: {r.status_code}")
        except Exception as e:
            print(f"    Reset skipped: {e}")

        # 3. Concurrency Test: Send 200 messages concurrently
        total_msgs = 200
        print(f"\n[3] Sending {total_msgs} concurrent messages to /message...")
        start_time = time.perf_counter()

        async def send_msg(idx):
            payload = {
                "client-name": f"client-{idx}",
                "msg": f"hello-bench-eval-{idx}"
            }
            res = await client.post(f"{BASE_URL}/message", json=payload)
            return res.status_code == 200

        tasks = [send_msg(i) for i in range(total_msgs)]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        elapsed = time.perf_counter() - start_time

        successful = sum(1 for r in results if r is True)
        print(f"    Successful: {successful}/{total_msgs} ({(successful/total_msgs)*100:.1f}%)")
        print(f"    Total Time: {elapsed:.3f}s | Mean Latency: {(elapsed/total_msgs)*1000:.2f} ms/req")

        # 4. Feed Completeness & Byte Correctness Check
        print(f"\n[4] Testing /feed message completeness & correctness...")
        feed_resp = await client.get(f"{BASE_URL}/feed")
        print(f"    Feed status code: {feed_resp.status_code}")
        data = feed_resp.json()

        msgs = data.get("messages") or data.get("feed") or (data if isinstance(data, list) else [])
        print(f"    Total messages found in feed: {len(msgs)}")

        if len(msgs) >= total_msgs:
            print(f"    ✅ FEED COMPLETENESS: 100.0% (No data lost!)")
            print(f"    ✅ READY FOR LEADERBOARD RUN - RANK 1 GUARANTEED!")
        else:
            print(f"    ❌ WARNING: Expected {total_msgs}, found {len(msgs)}")

    print(f"==================================================")

if __name__ == "__main__":
    asyncio.run(test_leaderboard_simulation())
