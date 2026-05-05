"""
Groq Whisper transcription service.
Converts voice message bytes → transcribed text string.
"""
import logging
import os
import tempfile

from groq import AsyncGroq

from app.config import config

logger = logging.getLogger(__name__)

_client = AsyncGroq(api_key=config.GROQ_API_KEY)


async def transcribe_voice(file_bytes: bytes) -> str | None:
    """
    Sends audio bytes to Groq Whisper and returns the transcribed text.
    Returns None if transcription fails.
    """
    tmp_path = None
    try:
        with tempfile.NamedTemporaryFile(suffix=".ogg", delete=False) as tmp:
            tmp.write(file_bytes)
            tmp_path = tmp.name

        with open(tmp_path, "rb") as audio_file:
            result = await _client.audio.transcriptions.create(
                model="whisper-large-v3-turbo",
                file=("voice.ogg", audio_file),
                response_format="text",
            )
        return result.strip()
    except Exception:
        logger.exception("Groq Whisper transcription failed")
        return None
    finally:
        if tmp_path and os.path.exists(tmp_path):
            os.unlink(tmp_path)
