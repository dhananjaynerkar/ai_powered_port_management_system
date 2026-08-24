import uvicorn

if __name__ == "__main__":
    uvicorn.run("pms_api.app:create_runtime_app", factory=True, host="127.0.0.1", port=8001, reload=False)
