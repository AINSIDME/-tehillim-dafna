#!/usr/bin/env python3
"""Hebrew Tehillim + short Hebrew explanation, private YouTube upload by default."""
import argparse
import asyncio
from datetime import datetime
from html import unescape
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile
from zoneinfo import ZoneInfo

import edge_tts
from PIL import Image, ImageDraw, ImageFont
import requests

NAME = "דפנה בת רבקה"
VOICE = os.getenv("HEBREW_VOICE", "he-IL-AvriNeural")
PRIVACY = os.getenv("YOUTUBE_PRIVACY", "private")
FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
STATE = Path("state.json")
OUT = Path("output")


def verses_for(chapter):
    r = requests.get(f"https://www.sefaria.org/api/texts/Psalms.{chapter}",
                     params={"context": 0, "commentary": 0}, timeout=45)
    r.raise_for_status()
    data = r.json()
    verses = [re.sub("<[^>]+>", "", unescape(v)).strip()
              for v in data.get("he", []) if isinstance(v, str)]
    verses = [v for v in verses if v]
    if not verses:
        raise RuntimeError("No se pudo leer el texto hebreo de Tehilim.")
    license_label = str(data.get("license", "")).lower()
    if "copyright" in license_label or "all rights reserved" in license_label:
        raise RuntimeError("La edición de Sefaria necesita permiso de reutilización.")
    return verses


def wrap(draw, text, font, width):
    lines, current = [], ""
    for word in text.split():
        trial = (current + " " + word).strip()
        if current and draw.textbbox((0, 0), trial, font=font, direction="rtl")[2] > width:
            lines.append(current)
            current = word
        else:
            current = trial
    if current:
        lines.append(current)
    return lines


def render_slide(text, chapter, label, filename):
    canvas = Image.new("RGB", (1280, 720), "#101b2d")
    draw = ImageDraw.Draw(canvas)
    gold = "#dfbe86"
    draw.rounded_rectangle((55, 50, 1225, 670), radius=28, outline=gold, width=3)
    header = ImageFont.truetype(FONT, 35)
    draw.text((640, 112), "לעילוי נשמת דפנה בת רבקה ע״ה",
              fill=gold, font=header, anchor="mm", direction="rtl")
    sub = ImageFont.truetype(FONT, 27)
    draw.text((640, 177), f"תהילים פרק {chapter} | {label}",
              fill="#c0cbd8", font=sub, anchor="mm", direction="rtl")
    size = 48
    font = ImageFont.truetype(FONT, size)
    lines = wrap(draw, text, font, 1030)
    while (len(lines) > 7 or len(lines) * (size + 16) > 380) and size > 24:
        size -= 3
        font = ImageFont.truetype(FONT, size)
        lines = wrap(draw, text, font, 1030)
    line_height = size + 19
    y = 350 - (len(lines) - 1) * line_height / 2
    for line in lines:
        draw.text((640, y), line, fill="#fff9ee", font=font,
                  anchor="mm", direction="rtl")
        y += line_height
    draw.text((640, 628), "לימוד יומי • לזכרה באהבה", fill=gold, font=sub,
              anchor="mm", direction="rtl")
    canvas.save(filename)


async def synthesize(text, filename):
    await edge_tts.Communicate(text, VOICE, rate="-12%").save(str(filename))


def ffmpeg(*args):
    subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", *map(str, args)],
                   check=True)


def create_video(chapter, verses, explanation, destination):
    OUT.mkdir(exist_ok=True)
    # Every segment includes its own narration and matching text.
    segments = [
        ("לעילוי נשמת דפנה בת רבקה. תהילים פרק " + str(chapter),
         "לעילוי נשמת דפנה בת רבקה", "פתיחה")
    ]
    segments += [(verse, verse, f"פסוק {i}") for i, verse in enumerate(verses, 1)]
    segments += [
        ("כעת נלמד הסבר קצר לפרק.", "הסבר קצר לפרק", "לימוד"),
        (explanation[0], explanation[0], "הסבר הפרק"),
        (explanation[1], explanation[1], "מסר לחיים"),
        ("יהי רצון שהלימוד יהיה לעילוי נשמת דפנה בת רבקה.",
         "יהי רצון שהלימוד יהיה לעילוי נשמת דפנה בת רבקה ע״ה", "סיום")
    ]
    with tempfile.TemporaryDirectory() as directory:
        temp = Path(directory)
        clips = []
        for i, (narration, screen_text, label) in enumerate(segments):
            png = temp / f"{i:04}.png"
            mp3 = temp / f"{i:04}.mp3"
            mp4 = temp / f"{i:04}.mp4"
            render_slide(screen_text, chapter, label, png)
            asyncio.run(synthesize(narration, mp3))
            ffmpeg("-loop", "1", "-i", png, "-i", mp3,
                   "-c:v", "libx264", "-preset", "veryfast", "-tune", "stillimage",
                   "-pix_fmt", "yuv420p", "-r", "24", "-c:a", "aac",
                   "-af", "apad=pad_dur=0.3", "-shortest", mp4)
            clips.append(mp4)
        playlist = temp / "concat.txt"
        playlist.write_text("".join("file '" + p.as_posix() + "'\n" for p in clips),
                            encoding="utf-8")
        ffmpeg("-f", "concat", "-safe", "0", "-i", playlist,
               "-c", "copy", "-movflags", "+faststart", destination)


def upload_video(filename, chapter, today):
    from google.oauth2.credentials import Credentials
    from google.auth.transport.requests import Request
    from googleapiclient.discovery import build
    from googleapiclient.http import MediaFileUpload

    token = os.environ.get("YOUTUBE_TOKEN_JSON")
    if not token:
        raise RuntimeError("Falta el secret YOUTUBE_TOKEN_JSON. No se subió ningún video.")
    credentials = Credentials.from_authorized_user_info(
        json.loads(token), scopes=["https://www.googleapis.com/auth/youtube.upload"])
    if not credentials.valid:
        if credentials.expired and credentials.refresh_token:
            credentials.refresh(Request())
        else:
            raise RuntimeError("OAuth inválido: vuelve a autorizar YouTube.")
    youtube = build("youtube", "v3", credentials=credentials, cache_discovery=False)
    req = youtube.videos().insert(
        part="snippet,status",
        body={
            "snippet": {
                "title": f"תהילים יומי | פרק {chapter} והסבר | לעילוי נשמת {NAME}",
                "description": (
                    f"תהילים פרק {chapter} | {today}\n"
                    f"קריאה והסבר קצר בעברית לעילוי נשמת {NAME} ע״ה.\n"
                    "ההסבר הוא תקציר מקורי ולא ציטוט מפרשן.\n"
                    "טקסט תהילים: Sefaria.org. קריינות: קול ממוחשב."
                ),
                "categoryId": "27",
                "defaultLanguage": "he",
                "tags": ["תהילים", "לימוד יומי", "לעילוי נשמת", "דפנה בת רבקה"]
            },
            "status": {"privacyStatus": PRIVACY, "selfDeclaredMadeForKids": False}
        },
        media_body=MediaFileUpload(str(filename), mimetype="video/mp4",
                                   resumable=True, chunksize=8 * 1024 * 1024)
    )
    response = None
    while response is None:
        _, response = req.next_chunk()
    return response["id"]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--upload", action="store_true")
    parser.add_argument("--chapter", type=int)
    args = parser.parse_args()
    today = datetime.now(ZoneInfo("Asia/Jerusalem")).date().isoformat()
    state = json.loads(STATE.read_text(encoding="utf-8"))
    if args.upload and state.get("last_date") == today:
        print("Ya se publicó hoy; no se duplicará.")
        return
    chapter = args.chapter or (int(state.get("last_chapter") or 0) % 150 + 1)
    if not 1 <= chapter <= 150:
        parser.error("El capítulo debe estar entre 1 y 150.")
    explanations = json.loads(Path("explanations.json").read_text(encoding="utf-8"))
    explanation = explanations.get(str(chapter))
    if not explanation or len(explanation) != 2:
        raise RuntimeError(f"Falta explicación revisada del capítulo {chapter}. "
                           "Deteniendo para no publicar contenido incompleto.")
    verses = verses_for(chapter)
    output = OUT / f"tehillim_{today}_chapter_{chapter}.mp4"
    create_video(chapter, verses, explanation, output)
    print("Vídeo generado:", output)
    if args.upload:
        video_id = upload_video(output, chapter, today)
        STATE.write_text(json.dumps({"last_chapter": chapter, "last_date": today,
                                     "last_video_id": video_id}, ensure_ascii=False, indent=2)
                         + "\n", encoding="utf-8")
        print("Publicado:", "https://www.youtube.com/watch?v=" + video_id)


if __name__ == "__main__":
    main()
