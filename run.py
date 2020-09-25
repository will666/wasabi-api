import os
from os.path import join, dirname
from dotenv import load_dotenv
import uvicorn

dotenv_path = join(dirname(__file__), ".env")
load_dotenv(dotenv_path)

if __name__ == "__main__":

    uvicorn.run(
        "src.main:app",
        host=os.getenv("SERVER_ADDRESS"),
        port=int(os.getenv("SERVER_PORT")),
        reload=os.getenv("SERVER_RELOAD"),
        debug=os.getenv("DEBUG"),
        workers=int(os.getenv("SERVER_WORKERS")),
    )
