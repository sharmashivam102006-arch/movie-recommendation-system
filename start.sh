#!/usr/bin/env bash
# Start FastAPI backend server in background on port 8000
uvicorn main:app --host 127.0.0.1 --port 8000 &

# Give FastAPI backend a few seconds to start
sleep 3

# Start Streamlit frontend server on Render's assigned $PORT
exec streamlit run app.py --server.port $PORT --server.address 0.0.0.0
