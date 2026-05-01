"""Semantic transcript chunking using LLM to create ~120-word sentence-complete paragraphs."""

import logging
import os
import sys

from openai import OpenAI


def chunk_transcript(transcript: str, target_words: int = 120) -> list[str]:
    """Break a transcript into logical paragraphs of approximately target_words each.

    Uses an LLM to ensure paragraphs end at complete sentence boundaries.

    Args:
        transcript: Full transcript text
        target_words: Approximate word count per paragraph (default 120)

    Returns:
        List of paragraph strings
    """
    logging.info(f"Chunking transcript into ~{target_words}-word paragraphs...")

    client = OpenAI(
        api_key=os.getenv('QWEN_CODING_API_KEY'),
        base_url=os.getenv('QWEN_CODING_BASE_URL')
    )

    prompt = (
        f"以下の日本語トランスクリプトを、約{target_words}語ずつの段落に分割してください。\n"
        "各段落は必ず完全な文の終わりで区切ってください。文中での分割は絶対にしないでください。\n"
        "段落は2つの改行（空行）で区切って出力してください。\n"
        "元のテキストの内容は一切変更しないでください。削除や追加も禁止です。\n"
        "トランスクリプト:\n\n"
        f"{transcript}"
    )

    try:
        response = client.chat.completions.create(
            model="qwen3-coder-plus",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "あなたはトランスクリプトの段落分割アシスタントです。"
                        "与えられたテキストを指定された語数で分割しますが、"
                        "必ず文の区切りで分割してください。"
                    )
                },
                {"role": "user", "content": prompt}
            ],
            max_tokens=8192,
            temperature=0.1
        )

        result = response.choices[0].message.content.strip()

        if not result:
            logging.error("Chunking returned empty result")
            sys.exit(1)

        paragraphs = [p.strip() for p in result.split('\n\n') if p.strip()]

        if not paragraphs:
            logging.error("No paragraphs produced from chunking")
            sys.exit(1)

        # Verify no content was lost (rough check)
        original_len = len(transcript.replace(' ', ''))
        chunked_len = len(''.join(paragraphs).replace(' ', ''))
        if chunked_len < original_len * 0.9:
            logging.warning(
                f"Chunking may have lost content: original={original_len} chars, "
                f"chunked={chunked_len} chars"
            )

        logging.info(f"Transcript chunked into {len(paragraphs)} paragraphs")
        return paragraphs

    except Exception as e:
        logging.exception(f"Error chunking transcript: {str(e)}")
        sys.exit(1)
