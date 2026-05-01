"""Word-by-word comparison between reference and user transcripts using LLM."""

import json
import logging
import os
import sys

from openai import OpenAI


def compare_transcripts(reference: str, user_transcript: str) -> dict:
    """Compare a user's spoken transcript against the reference.

    Returns a structured diff showing correct words, substitutions, missing words, and extra words.

    Args:
        reference: The correct reference transcript
        user_transcript: What the user actually said

    Returns:
        dict with keys:
            - diffs: list of {status, ref, user} objects
            - accuracy: float 0-100
            - missing: list of missing words/phrases
            - extras: list of extra words/phrases
    """
    logging.info("Comparing user transcript against reference...")

    client = OpenAI(
        api_key=os.getenv('QWEN_CODING_API_KEY'),
        base_url=os.getenv('QWEN_CODING_BASE_URL')
    )

    prompt = (
        "Compare the reference transcript with the user's spoken transcript word-by-word.\n"
        "Return ONLY a valid JSON object with this exact structure:\n"
        "{\n"
        '  "diffs": [\n'
        '    {"status": "correct", "ref": "word", "user": "word"},\n'
        '    {"status": "wrong", "ref": "expected_word", "user": "actual_word"},\n'
        '    {"status": "missing", "ref": "word", "user": null},\n'
        '    {"status": "extra", "ref": null, "user": "word"}\n'
        "  ],\n"
        '  "accuracy": 75.5,\n'
        '  "missing": ["word1", "word2"],\n'
        '  "extras": ["word3"]\n'
        "}\n\n"
        "Rules:\n"
        "- For Japanese, segment into meaningful word units (morphemes), not individual characters.\n"
        "- Match words as closely as possible in order.\n"
        "- 'correct': user said the right word\n"
        "- 'wrong': user said a different word instead of the reference word\n"
        "- 'missing': reference word was not spoken by the user\n"
        "- 'extra': user said a word not in the reference\n"
        "- accuracy should be: (correct_count / total_reference_words) * 100\n"
        "- missing list: all words the user failed to say\n"
        "- extras list: all extra words the user added\n"
        "- Do NOT include any text outside the JSON object.\n\n"
        f"Reference: {reference}\n\n"
        f"User transcript: {user_transcript}"
    )

    try:
        response = client.chat.completions.create(
            model="qwen3-coder-plus",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a transcript comparison assistant for language learning. "
                        "You always return ONLY valid JSON, never markdown or explanation."
                    )
                },
                {"role": "user", "content": prompt}
            ],
            max_tokens=4096,
            temperature=0.0
        )

        result_text = response.choices[0].message.content.strip()

        # Strip markdown code fences if present
        if result_text.startswith('```'):
            result_text = result_text.split('\n', 1)[1]
            if result_text.endswith('```'):
                result_text = result_text.rsplit('\n', 1)[0]
            result_text = result_text.strip()

        diff_data = json.loads(result_text)

        # Validate structure
        if 'diffs' not in diff_data:
            logging.error("Comparison response missing 'diffs' field")
            sys.exit(1)

        logging.info(
            f"Comparison complete: accuracy={diff_data.get('accuracy', 'N/A')}%, "
            f"diffs={len(diff_data['diffs'])}"
        )

        return diff_data

    except json.JSONDecodeError as e:
        logging.exception(f"Failed to parse comparison JSON: {str(e)}")
        logging.debug(f"Raw response: {result_text}")
        sys.exit(1)
    except Exception as e:
        logging.exception(f"Error comparing transcripts: {str(e)}")
        sys.exit(1)
