import requests
from datetime import datetime, timezone
from curator.autopost import settings
from library.models import CodebaseRelease


BLUESKY_HANDLE = "test266.bsky.social"
BLUESKY_APP_PASSWORD = "password"

class Autopost:
    def __init__(self):
        self.identifier = settings.BLUESKY_HANDLE
        self.password = settings.BLUESKY_APP_PASSWORD
        self.access_token = None
        self.did = None

    def authenticate(self):
        #handle authentication here
        response = requests.post(
            "https://bsky.social/xrpc/com.atproto.server.createSession",
            json={
                "identifier": self.identifier,
                "password": self.password,
            },
        )
        response.raise_for_status()
        session = response.json()
        self.access_token = session["accessJwt"]
        self.did = session["did"]

    def create_post(self, text):
        #create a post here and post to bluesky
        if not self.access_token or not self.did:
            raise ValueError("Must authenticate before creating a post.")
        
        
        post_content = {
            "$type": "app.bsky.feed.post",
            "text": text,
            "createdAt": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        }

        response = requests.post(
            "https://bsky.social/xrpc/com.atproto.repo.createRecord",
            headers={"Authorization": f"Bearer {self.access_token}"},
            json={
                "repo": self.did,
                "collection": "app.bsky.feed.post",
                "record": post_content,
            },
        )
        response.raise_for_status()
        return response.json()
    
 
def autopost_to_bluesky(text):
        #function to autopost to Bluesky.
        autopost = Autopost()
        autopost.authenticate()
        return autopost.create_post(text)

