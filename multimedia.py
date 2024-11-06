import requests
import base64
from pydub import AudioSegment
from io import BytesIO


def get_cropped_audio(url, start_time, end_time):
    response = requests.get(url)
    response.raise_for_status()
    audio = AudioSegment.from_file(BytesIO(response.content))

    start_ms = start_time * 1000
    end_ms = end_time * 1000

    print("Audio cropped", url, start_time, end_time)
    cropped_audio = audio[start_ms:end_ms]
    audio_bytes = BytesIO()
    cropped_audio.export(audio_bytes, format="ogg")
    audio_bytes.seek(0)

    return base64.b64encode(audio_bytes.read()).decode('utf-8')
