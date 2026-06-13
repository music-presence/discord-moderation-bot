import json
import requests
import os
import sys
import pathlib
from urllib.parse import urlparse

from snowflake import Snowflake


# https://docs.discord.com/developers/reference#convert-snowflake-to-datetime
DISCORD_EPOCH = 1420070400000


with open("download.json", "r") as f:
    j = json.load(f)
    for mid, group in j.items():
        snowflake = Snowflake.parse(int(mid), DISCORD_EPOCH)
        directory = os.path.join(
            "downloads", snowflake.datetime.strftime("%Y%m%d%H%M%S")
        )
        if os.path.exists(directory):
            continue
        pathlib.Path(directory).mkdir(exist_ok=False, parents=True)
        for index, url in enumerate(group):
            parsed_url = urlparse(url)
            name, ext = os.path.splitext(os.path.basename(parsed_url.path))
            target_path = f"./{directory}/{index}-{name}{ext}"
            print(f"{target_path}")
            try:
                request = requests.get(url)
                with open(target_path, "wb") as handler:
                    handler.write(request.content)
            except Exception as e:
                print(f"ERROR {e}", file=sys.stderr)
