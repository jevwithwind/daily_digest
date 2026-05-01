"""Email sending via Resend API."""

import logging
import os
import sys

import resend


def format_transcript_for_email(transcript: str) -> str:
    """Format the transcript with paragraph breaks every ~500 chars at nearest punctuation."""
    if len(transcript) <= 500:
        return transcript

    formatted = []
    start = 0

    while start < len(transcript):
        end = start + 500

        if end >= len(transcript):
            formatted.append(transcript[start:])
            break

        segment = transcript[start:end]
        punct_positions = []

        for i, char in enumerate(segment):
            if char in ['。', '！', '？', '.', '!', '?']:
                punct_positions.append(i)

        if punct_positions:
            last_punct = punct_positions[-1]
            actual_end = start + last_punct + 1
            formatted.append(transcript[start:actual_end].strip())
            start = actual_end
        else:
            formatted.append(transcript[start:end].strip())
            start = end

    return '\n\n'.join(formatted)


def send_email(video_info: dict, summary: str, transcript: str):
    """Send the email with video info, summary, and transcript."""
    logging.info("Sending email...")

    resend.api_key = os.getenv('RESEND_API_KEY')

    subject = f"[Pivot Talk] {video_info['title']} - {video_info['formatted_date']}"

    formatted_transcript = format_transcript_for_email(transcript)

    email_body = f"""🔗 動画リンク: {video_info['url']}

📝 要約:
{summary}

────────────────────────────

📖 トランスクリプト:

{formatted_transcript}
"""

    try:
        params = {
            "from": os.getenv('EMAIL_FROM'),
            "to": os.getenv('EMAIL_TO'),
            "subject": subject,
            "text": email_body,
        }

        email = resend.Emails.send(params)
        logging.info(f"Email sent successfully with ID: {email['id']}")

    except Exception as e:
        logging.exception(f"Error sending email: {str(e)}")
        sys.exit(1)
