import string
from textwrap import dedent


def text(message: string):
    return {"type": "text", "data": {"text": dedent(message)}}


def image(url: string):
    return {"type": "image", "data": {"file": url}}


def audio(url: string):
    return {"type": "record", "data": {"file": url}}
