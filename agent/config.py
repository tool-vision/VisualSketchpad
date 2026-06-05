import os
from pathlib import Path


def load_dotenv(path):
    if not path.exists():
        return
    for raw_line in path.read_text().splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip("\"'")
        if key and key not in os.environ:
            os.environ[key] = value


load_dotenv(Path(__file__).resolve().parents[1] / ".env")

# set up the agent
MAX_REPLY = 10

# set up the LLM for the agent
os.environ.setdefault("AUTOGEN_USE_DOCKER", "False")
OPENAI_MODEL = os.environ.get("OPENAI_MODEL", "gpt-4o")
config_list = []
for env_name in ("OPENAI_API_KEY", "OPENAI_API_KEY_BACKUP"):
    api_key = os.environ.get(env_name)
    if api_key:
        config_list.append({"model": OPENAI_MODEL, "temperature": 0.0, "api_key": api_key})
if not config_list:
    config_list.append({"model": OPENAI_MODEL, "temperature": 0.0, "api_key": None})
llm_config={"cache_seed": None, "config_list": config_list}


# use this after building your own server. You can also set up the server in other machines and paste them here.
SOM_ADDRESS = os.environ.get("SOM_ADDRESS", "http://localhost:8080/")
GROUNDING_DINO_ADDRESS = os.environ.get("GROUNDING_DINO_ADDRESS", "http://localhost:8081/")
DEPTH_ANYTHING_ADDRESS = os.environ.get("DEPTH_ANYTHING_ADDRESS", "http://localhost:8082/")
