import os
os.environ["RUNTIME_ENV"] = "integration"
from origami_api.config import Config
config = Config()
print("hasattr server:", hasattr(config, "server"))
server_cfg = getattr(config, "server", None)
print("server_cfg:", server_cfg)
if server_cfg:
    print("hasattr routers:", hasattr(server_cfg, "routers"))
    print("routers:", getattr(server_cfg, "routers", None))
