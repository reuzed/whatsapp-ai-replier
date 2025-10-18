"""Utility for generating images via OpenAI and saving to top-level temp folder."""

from __future__ import annotations

import base64
import os
from pathlib import Path
from typing import Optional

from loguru import logger
from openai import OpenAI  # type: ignore[import-not-found]

from src.config import settings


TEMP_DIR_NAME = "temp"


def get_repo_root() -> Path:
    """Return repository root resolved from this file location."""
    return Path(__file__).resolve().parent.parent


def ensure_temp_dir(repo_root: Optional[Path] = None) -> Path:
    """Ensure the top-level temp directory exists and return its path."""
    root = repo_root or get_repo_root()
    temp_dir = root / TEMP_DIR_NAME
    temp_dir.mkdir(parents=True, exist_ok=True)
    return temp_dir


def _get_openai_client() -> OpenAI:
    """Instantiate and return an OpenAI client using settings.openai_api_key."""
    api_key = settings.openai_api_key
    if not api_key:
        raise RuntimeError(
            "OPENAI_API_KEY is not set. Add it to your .env as OPENAI_API_KEY=..."
        )
    # The SDK reads from env by default, but pass explicitly to be safe
    os.environ.setdefault("OPENAI_API_KEY", api_key)
    return OpenAI(api_key=api_key)


def generate_image(
    prompt: str,
    *,
    model: str = "gpt-image-1",
    size: str = "1024x1024",
    n: int = 1,
    output_filename: Optional[str] = None,
    repo_root: Optional[Path] = None,
) -> list[Path]:
    """
    Generate one or more images from a prompt and save them under top-level temp/.

    Returns a list of file paths to the saved images.
    """
    if n < 1:
        raise ValueError("n must be >= 1")

    client = _get_openai_client()
    logger.info(f"Generating {n} image(s) with model={model}, size={size}")

    result = client.images.generate(
        model=model,
        prompt=prompt,
        n=n,
        size=size,
    )

    temp_dir = ensure_temp_dir(repo_root)
    saved_paths: list[Path] = []

    for idx, data in enumerate(result.data):  # type: ignore[attr-defined]
        # SDK returns base64 JSON for each image
        b64 = getattr(data, "b64_json", None)
        if not b64:
            logger.warning("No b64_json found for an image result; skipping")
            continue
        image_bytes = base64.b64decode(b64)

        base_name = output_filename or "generated_image"
        suffix = "" if n == 1 else f"_{idx+1}"
        filename = f"{base_name}{suffix}.png"
        out_path = temp_dir / filename

        with open(out_path, "wb") as f:
            f.write(image_bytes)

        logger.info(f"Saved image to {out_path}")
        saved_paths.append(out_path)

    if not saved_paths:
        raise RuntimeError("Image generation did not yield any images")

    return saved_paths


if __name__ == "__main__":
    # Simple test: generate a picture of some dogs
    try:
        paths = generate_image(
            prompt="A high-quality photo of a group of playful dogs in a park",
            n=1,
            size="1024x1024",
            output_filename="dogs_test",
        )
        print("Generated:", ", ".join(str(p) for p in paths))
    except Exception as e:
        logger.error(f"Failed generating test image: {e}")

