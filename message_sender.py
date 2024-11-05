import string
import requests
from message_builder import text

llob_http_endpoint = "http://localhost:3000"


def init(endpoint):
    global llob_http_endpoint
    llob_http_endpoint = endpoint


def group_send(group_id: int, messages: list):
    requests.post(
        f"{llob_http_endpoint}/send_group_msg",
        json={
            "group_id": group_id,
            "message": [
                *messages,
            ],
        },
    )
    print("Sent message(s)", messages)


def group_respond(
    group_id: int, message_id: int, sender_id: int, sender_name: string, messages: list
):
    group_send(
        group_id,
        [
            {"type": "reply", "data": {"id": message_id}},
            {"type": "at", "data": {"qq": sender_id, "name": sender_name}},
            text("\n"),
            *messages,
        ],
    )
