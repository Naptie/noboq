import string
import uvicorn

import message_sender
import phizone
import db_utils as db
from fastapi import FastAPI, Request
from yaml import safe_load
from message_sender import group_respond

groups_to_listen = []

app = FastAPI()


def process_command_text(
    group_id: int,
    message_id: int,
    sender_id: int,
    sender_name: string,
    args: list[string],
):
    match args[0].lower():
        case "phizone" | "pz":
            if len(args) < 2:
                return phizone.handle_root(sender_id)
            match args[1].lower():
                case "bind":
                    return phizone.handle_bind(sender_id, args[2:])
                case "unbind":
                    return phizone.handle_unbind(sender_id)
                case "pb" | "b19" | "b":
                    return phizone.handle_personal_bests(
                        group_id, message_id, sender_id, sender_name, args[2:]
                    )
                case "chartsearch" | "search" | "cs" | "sc" | "s":
                    return phizone.handle_search_chart(args[2:])
                case (
                    "chartquery"
                    | "chartinfo"
                    | "query"
                    | "info"
                    | "cq"
                    | "qc"
                    | "q"
                    | "i"
                ):
                    return phizone.handle_query_chart(group_id, args[2:])
                case "randomchart" | "random" | "rc" | "r":
                    return phizone.handle_random_chart(group_id)
    return None


def process_group_message(
    group_id: int,
    message_id: int,
    sender_id: int,
    sender_name: string,
    message,
    raw_message: string,
):
    if raw_message.startswith("/"):
        text_args = [
            f
            for e in message
            if e["type"] == "text"
            for f in e["data"]["text"].split(" ")
        ]
        text_args[0] = text_args[0][1:]
        results = process_command_text(
            group_id, message_id, sender_id, sender_name, text_args
        )
        if results is not None:
            group_respond(group_id, message_id, sender_id, sender_name, results)


@app.post("/")
async def root(request: Request):
    data = await request.json()
    if "message_type" in data:
        if data["message_type"] == "group":
            if data["group_id"] in groups_to_listen:
                print(data)
                process_group_message(
                    data["group_id"],
                    data["message_id"],
                    data["sender"]["user_id"],
                    data["sender"]["card"],
                    data["message"],
                    data["raw_message"],
                )
        else:
            print(data)
    else:
        print(data)
    return {}


def load():
    global groups_to_listen
    with open("config.yml", "r") as file:
        content = safe_load(file)
        llob_http_endpoint = content["llob-http-endpoint"]
        phizone_api = content["phizone-api"]
        groups_to_listen = content["groups-to-listen"]
        connection_string = content["mongodb"]
    message_sender.init(llob_http_endpoint)
    db.init(connection_string)
    phizone.init(phizone_api)


if __name__ == "__main__":
    load()
    uvicorn.run(app, port=8080)
