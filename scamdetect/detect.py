import os
import regex
import sys
import json
from dataclasses import dataclass
from io import BytesIO
import warnings

import discord
import pytesseract
from PIL import Image, ImageEnhance, ImageFilter, ImageOps

warnings.filterwarnings(
    "ignore",
    message="Truncated File Read",
    category=UserWarning,
)


SCAM_PHRASE_COUNT_THRESHOLD = 3
BLACKLIST_FILENAME = "blacklist.txt"


with open(os.path.join(os.path.dirname(__file__), BLACKLIST_FILENAME)) as file:
    blacklist_phrases = [
        line.strip() for line in file.readlines() if len(line.strip()) > 0
    ]
    blacklist_patterns = [
        regex.compile(
            # Allow errors, if there are no symbols in the phrase and if the
            # phrase exceeds a certain minimum length.
            (
                phrase
                if (
                    "\\." in phrase
                    or "," in phrase
                    or "\\$" in phrase
                    or len(phrase) <= 6
                )
                else f"({phrase}){{e<=1}}"
            ),
            regex.MULTILINE | regex.IGNORECASE,
        )
        for phrase in blacklist_phrases
    ]

# print(json.dumps([p.pattern for p in blacklist_patterns], indent=2))


def image_from_data(data: bytes) -> Image:
    return Image.open(BytesIO(data))


def enhanced_image(image: Image) -> Image:
    image = image.filter(ImageFilter.UnsharpMask(radius=5, percent=100, threshold=3))
    return image


def image_to_text(image: Image) -> str:
    # https://pyimagesearch.com/2021/11/15/tesseract-page-segmentation-modes-psms-explained-how-to-improve-your-ocr-accuracy/
    # PSM 11: Sparse text. Find as much text as possible in no particular order.
    text = pytesseract.image_to_string(image, config="--psm 11")
    # Normalize whitespace, just in case.
    return " ".join(text.split())


def find_text_scam_phrases(text: str, debug_log: bool = False) -> list[str]:
    matches = []
    for pattern in blacklist_patterns:
        match = pattern.search(text)
        if match is not None:
            i, j = match.span()
            match_text = text[i:j].lower().strip()
            if debug_log:
                print(f"MATCH {match_text}")
            matches.append(match_text)
    return matches


@dataclass
class ScamScanResult:
    is_scam: bool
    phrases: list[str]


async def scan_discord_attachments_for_scams(
    attachments: list[discord.Attachment],
) -> ScamScanResult:
    if len(attachments) == 0:
        return False
    # Count the number of scam phrases and once we reach a specific threshold,
    # consider the list of attachments a scam. Start with the last image, since
    # that is usually the "success" one that contains lots of blacklisted
    # phrases. This should improve scam recognition times.
    found_scam_phrases = []
    attachment_images = []
    detection_count = 0
    for attachment in reversed(attachments):
        try:
            data = await attachment.read(use_cached=True)
            image = image_from_data(data)
            attachment_images.append(image)
            scam_phrases = find_text_scam_phrases(image_to_text(image))
            detection_count += 1
            found_scam_phrases.extend(scam_phrases)
        except Exception as e:
            print(f"Error: Failed to read attachment for scam phrase detection: {e}")
            continue
        if len(found_scam_phrases) >= SCAM_PHRASE_COUNT_THRESHOLD:
            break
    second_pass = False
    if len(found_scam_phrases) < SCAM_PHRASE_COUNT_THRESHOLD:
        found_scam_phrases = []
        second_pass = True
        for image in attachment_images:
            try:
                image = enhanced_image(image)
                scam_phrases = find_text_scam_phrases(image_to_text(image))
                detection_count += 1
                found_scam_phrases.extend(scam_phrases)
            except Exception as e:
                print(
                    f"Error: Failed to read enhanced attachment for scam phrase detection: {e}"
                )
            continue
            found_scam_phrases.extend(scam_phrases)
            if len(found_scam_phrases) >= SCAM_PHRASE_COUNT_THRESHOLD:
                break
    result = ScamScanResult(
        is_scam=len(found_scam_phrases) >= SCAM_PHRASE_COUNT_THRESHOLD,
        phrases=found_scam_phrases,
    )
    print(
        f"Scanned Discord attachments: "
        f"is_scam={result.is_scam} detection_count={detection_count} "
        f"second_pass={second_pass} phrases={found_scam_phrases}"
    )
    return result


if __name__ == "__main__":
    path = sys.argv[1]
    print(path)
    with open(path, "rb") as file:
        data = file.read()
        image = image_from_data(data)
        text = image_to_text(image)
        print("NORMAL", len(text), text)
        n = find_text_scam_phrases(text, debug_log=True)
        print(n)

        eimage = enhanced_image(image)
        eimage.save("out.jpg")
        etext = image_to_text(eimage)
        print("ENHANCED", len(etext), etext)
        m = find_text_scam_phrases(etext, debug_log=True)
        print(m)
