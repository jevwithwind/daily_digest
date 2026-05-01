"""Text summarization using Qwen API."""

import logging
import os
import sys

from openai import OpenAI


def summarize_text(transcript: str) -> str:
    """Summarize the transcript in Japanese using Qwen Coding Plan API."""
    logging.info("Summarizing transcript...")

    coding_client = OpenAI(
        api_key=os.getenv('QWEN_CODING_API_KEY'),
        base_url=os.getenv('QWEN_CODING_BASE_URL')
    )

    try:
        response = coding_client.chat.completions.create(
            model="qwen3-coder-plus",
            messages=[
                {
                    "role": "system",
                    "content": "あなたはポッドキャストの要約アシスタントです。以下のトランスクリプトを日本語で簡潔に要約してください。箇条書きは使わず、1つの段落にまとめてください。"
                },
                {
                    "role": "user",
                    "content": transcript
                }
            ],
            max_tokens=1024
        )

        summary = response.choices[0].message.content

        if not summary.strip():
            logging.error("Summary generation returned empty result")
            sys.exit(1)

        logging.info("Summary generated")
        return summary

    except Exception as e:
        logging.exception(f"Error generating summary: {str(e)}")
        sys.exit(1)
