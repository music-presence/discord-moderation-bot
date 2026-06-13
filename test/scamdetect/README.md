# Test images for scam detection

This directory contains scripts to download images in bulk that were sent by compromised Discord accounts and which contain malicious content such as scam attempts.

1. Copy `download.example.json` to `download.json`
2. Enter message IDs and the corresponding Discord image URLs to download
3. Note that Discord links expire, so don't take too long collecting them
4. Run the download.py script to download the images

The Discord message ID is a "Snowflake ID" which contains a timestamp and is used to create meaningful folder names, it doesn't have to be accurate, it's just there to help it stay organized. The file name of the downloaded file is in the format `{N}_{NAME}` where `N` is the index in the JSON array (that should be the order of the image in the original message) and `NAME` is the original file name (which can be used for analysis as well).

The script does not redownload images for message IDs that already have a folder.
