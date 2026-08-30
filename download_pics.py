#!/usr/bin/env python3
"""Download and convert card pictures that have not been processed yet."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent
CARDS_FILE = ROOT / "cardtext-proj" / "cards.json"
CONVERTED_FILE = ROOT / "converted-pics.txt"
PICS_DIR = ROOT / "pics"
THUMBS_DIR = PICS_DIR / "thumb"
YIHUA_DIR = ROOT / "yihua"
IMAGE_URL = "https://cdn.233.momobako.com/ygoimg/ygopro/{card_id}.webp"
SUPER_PRE_IMAGE_URL = (
    "https://cdntx.moecube.com/ygopro-super-pre/data/pics/{card_id}.jpg"
)
SUPER_PRE_DATA_URL = (
    "https://cdncf.moecube.com/ygopro-super-pre/data/test-release-v2.json"
)
SLEEP_SECONDS = 1
MAX_CARD_ID = 99_999_999


class ImageNotFoundError(Exception):
    """The image server returned HTTP 404 for a card ID."""


def load_card_ids(path: Path) -> list[int]:
    with path.open(encoding="utf-8") as file:
        cards: Any = json.load(file)

    if not isinstance(cards, dict):
        raise ValueError(f"{path} 的顶层必须是 JSON 对象")

    card_ids: list[int] = []
    seen: set[int] = set()
    for card in cards.values():
        if not isinstance(card, dict):
            continue
        card_id = card.get("id")
        if isinstance(card_id, bool):
            continue
        try:
            card_id = int(card_id)
        except (TypeError, ValueError):
            continue
        if 0 < card_id <= MAX_CARD_ID and card_id not in seen:
            seen.add(card_id)
            card_ids.append(card_id)
    return card_ids


def load_super_pre_ids(url: str) -> list[int]:
    request = urllib.request.Request(
        url, headers={"User-Agent": "ygo-picture-downloader/1.0"}
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        cards: Any = json.load(response)

    if not isinstance(cards, list):
        raise ValueError("超先行卡数据的顶层必须是 JSON 数组")

    card_ids: list[int] = []
    seen: set[int] = set()
    for card in cards:
        if not isinstance(card, dict):
            continue
        card_id = card.get("id")
        if isinstance(card_id, bool):
            continue
        try:
            card_id = int(card_id)
        except (TypeError, ValueError):
            continue
        if len(str(card_id)) == 9 and card_id not in seen:
            seen.add(card_id)
            card_ids.append(card_id)
    return card_ids


def load_converted(path: Path) -> set[int]:
    if not path.exists():
        return set()

    converted: set[int] = set()
    with path.open(encoding="utf-8") as file:
        for line_number, line in enumerate(file, start=1):
            value = line.strip()
            if not value:
                continue
            try:
                converted.add(int(value))
            except ValueError:
                print(
                    f"警告：忽略 {path} 第 {line_number} 行的无效卡密：{value!r}",
                    file=sys.stderr,
                )
    return converted


def download_and_convert(card_id: int, image_url: str = IMAGE_URL) -> None:
    PICS_DIR.mkdir(parents=True, exist_ok=True)
    THUMBS_DIR.mkdir(parents=True, exist_ok=True)
    output_path = PICS_DIR / f"{card_id}.jpg"
    thumb_output_path = THUMBS_DIR / f"{card_id}.jpg"

    webp_fd, webp_name = tempfile.mkstemp(
        prefix=f".{card_id}-", suffix=".webp", dir=PICS_DIR
    )
    os.close(webp_fd)
    jpg_fd, jpg_name = tempfile.mkstemp(
        prefix=f".{card_id}-", suffix=".jpg", dir=PICS_DIR
    )
    os.close(jpg_fd)
    thumb_fd, thumb_name = tempfile.mkstemp(
        prefix=f".{card_id}-", suffix=".jpg", dir=THUMBS_DIR
    )
    os.close(thumb_fd)
    webp_path = Path(webp_name)
    jpg_path = Path(jpg_name)
    thumb_path = Path(thumb_name)

    try:
        request = urllib.request.Request(
            image_url.format(card_id=card_id),
            headers={"User-Agent": "ygo-picture-downloader/1.0"},
        )
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                with webp_path.open("wb") as file:
                    while chunk := response.read(64 * 1024):
                        file.write(chunk)
        except urllib.error.HTTPError as error:
            if error.code == 404:
                raise ImageNotFoundError(card_id) from error
            raise

        subprocess.run(
            [
                "magick",
                str(webp_path),
                "-define",
                "jpeg:extent=70KB",
                str(jpg_path),
            ],
            check=True,
        )
        subprocess.run(
            ["magick", str(jpg_path), "-resize", "49x70!", str(thumb_path)],
            check=True,
        )
        jpg_path.replace(output_path)
        thumb_path.replace(thumb_output_path)
    finally:
        webp_path.unlink(missing_ok=True)
        jpg_path.unlink(missing_ok=True)
        thumb_path.unlink(missing_ok=True)


def mark_converted(path: Path, card_id: int) -> None:
    with path.open("a", encoding="utf-8") as file:
        file.write(f"{card_id}\n")
        file.flush()
        os.fsync(file.fileno())


def write_yihua(card_id: int, yihua_ids: list[int]) -> None:
    output_path = YIHUA_DIR / str(card_id)
    if not yihua_ids:
        output_path.unlink(missing_ok=True)
        return

    YIHUA_DIR.mkdir(parents=True, exist_ok=True)
    fd, temporary_name = tempfile.mkstemp(prefix=f".{card_id}-", dir=YIHUA_DIR)
    temporary_path = Path(temporary_name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as file:
            for yihua_id in yihua_ids:
                file.write(f"{yihua_id}\n")
            file.flush()
            os.fsync(file.fileno())
        temporary_path.replace(output_path)
    finally:
        temporary_path.unlink(missing_ok=True)


def process_card(card_id: int, is_super_pre: bool = False) -> list[int]:
    """Download one card and its consecutive alternate artworks."""
    image_url = SUPER_PRE_IMAGE_URL if is_super_pre else IMAGE_URL
    download_and_convert(card_id, image_url)
    print(f"已保存到 pics/{card_id}.jpg", flush=True)
    time.sleep(SLEEP_SECONDS)

    if is_super_pre:
        return []

    yihua_ids: list[int] = []
    candidate_id = card_id + 1
    while candidate_id <= MAX_CARD_ID:
        print(f"  正在尝试异画 {candidate_id} ...", flush=True)
        try:
            download_and_convert(candidate_id)
        except ImageNotFoundError:
            print(f"  {candidate_id} 返回 404，异画探测结束。", flush=True)
            break

        yihua_ids.append(candidate_id)
        print(f"  已保存异画到 pics/{candidate_id}.jpg", flush=True)
        time.sleep(SLEEP_SECONDS)
        candidate_id += 1

    write_yihua(card_id, yihua_ids)
    return yihua_ids


def main() -> int:
    try:
        card_ids = load_card_ids(CARDS_FILE)
        super_pre_ids = load_super_pre_ids(SUPER_PRE_DATA_URL)
        converted = load_converted(CONVERTED_FILE)
    except (OSError, ValueError, json.JSONDecodeError) as error:
        print(f"读取数据失败：{error}", file=sys.stderr)
        return 1

    all_cards = [(card_id, False) for card_id in card_ids]
    all_cards.extend((card_id, True) for card_id in super_pre_ids)
    pending = [card for card in all_cards if card[0] not in converted]
    print(
        f"共找到 {len(card_ids)} 个正式卡密和 {len(super_pre_ids)} 个超先行卡密，"
        f"其中 {len(pending)} 个待处理。"
    )

    for index, (card_id, is_super_pre) in enumerate(pending, start=1):
        print(f"[{index}/{len(pending)}] 正在处理 {card_id} ...", flush=True)
        try:
            yihua_ids = process_card(card_id, is_super_pre)
            mark_converted(CONVERTED_FILE, card_id)
        except ImageNotFoundError:
            print(f"处理 {card_id} 失败：原图返回 404", file=sys.stderr, flush=True)
        except (OSError, subprocess.CalledProcessError, urllib.error.URLError) as error:
            print(f"处理 {card_id} 失败：{error}", file=sys.stderr, flush=True)
        else:
            print(
                f"{card_id} 处理完成，共找到 {len(yihua_ids)} 张异画。",
                flush=True,
            )

        if index < len(pending):
            time.sleep(SLEEP_SECONDS)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
