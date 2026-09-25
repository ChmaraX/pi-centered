#!/usr/bin/env python3
"""Write a Pi session file with one fixed exchange: make-session.py <question> <reply.md> <out.jsonl>"""
import json, sys, time, uuid, os
question, reply_path, out = sys.argv[1], sys.argv[2], sys.argv[3]
now = int(time.time() * 1000)
iso = time.strftime("%Y-%m-%dT%H:%M:%S.000Z", time.gmtime())
usage = {"input": 0, "output": 0, "cacheRead": 0, "cacheWrite": 0, "totalTokens": 0,
         "cost": {"input": 0, "output": 0, "cacheRead": 0, "cacheWrite": 0, "total": 0}}
entries = [
    {"type": "session", "version": 3, "id": str(uuid.uuid4()), "timestamp": iso, "cwd": os.path.dirname(os.path.abspath(out))},
    {"type": "message", "id": "a0000001", "parentId": None, "timestamp": iso,
     "message": {"role": "user", "content": question, "timestamp": now}},
    {"type": "message", "id": "a0000002", "parentId": "a0000001", "timestamp": iso,
     "message": {"role": "assistant", "content": [{"type": "text", "text": open(reply_path).read().strip()}],
                 "api": "anthropic-messages", "provider": "anthropic", "model": "claude-sonnet-4-5",
                 "usage": usage, "stopReason": "stop", "timestamp": now}},
]
with open(out, "w") as f:
    f.writelines(json.dumps(e) + "\n" for e in entries)
