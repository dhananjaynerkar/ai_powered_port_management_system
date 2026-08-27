import uvicorn

if __name__ == "__main__":
    # One worker keeps the process-local CrossEncoder and Ollama request gate
    # from being duplicated on the constrained local CPU host.
    uvicorn.run("pms_api.app:create_runtime_app", factory=True, host="127.0.0.1", port=8001, reload=False, workers=1)
