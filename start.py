import os
import sys
import uvicorn

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    host = "0.0.0.0"
    print(f"--> Sutra Production Server starting on {host}:{port}", flush=True)
    uvicorn.run("backend.main:app", host=host, port=port, log_level="info")
