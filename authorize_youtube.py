"""Execute locally, never commit the resulting credential files."""
import json
from google_auth_oauthlib.flow import InstalledAppFlow

flow = InstalledAppFlow.from_client_secrets_file(
    "client_secret.json", ["https://www.googleapis.com/auth/youtube.upload"])
credentials = flow.run_local_server(port=0)
with open("youtube_token.json", "w", encoding="utf-8") as f:
    json.dump(json.loads(credentials.to_json()), f, ensure_ascii=False, indent=2)
print("Token generado en youtube_token.json. No lo subas al repositorio.")
