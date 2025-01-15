import environ

env = environ.Env()
environ.Env.read_env()  

BLUESKY_HANDLE = env("BLUESKY_HANDLE", default="default_handle")
BLUESKY_APP_PASSWORD = env("BLUESKY_APP_PASSWORD", default="default_password")
