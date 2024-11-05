import os
import requests
from pydub import AudioSegment
from io import BytesIO


def crop_audio(url, start_time, end_time, output_file):
    response = requests.get(url)
    response.raise_for_status()
    output_dir = os.path.dirname(output_file)
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    audio = AudioSegment.from_file(BytesIO(response.content))

    start_ms = start_time * 1000
    end_ms = end_time * 1000

    cropped_audio = audio[start_ms:end_ms]

    cropped_audio.export(output_file, format="ogg")
    print(f"Audio segment saved as {output_file}")
