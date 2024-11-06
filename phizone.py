import math
import pytz
import re
import string
import threading
from datetime import datetime
from textwrap import dedent

import requests
import db_utils as db
from message_builder import text, audio, image
from message_sender import group_send
from miscellaneous import get_greeting
from multimedia import get_cropped_audio

api = "https://api.phizone.cn"
exp_list = [0, 50, 100, 500, 1000, 3000, 6000, 10000, 30000, 60000, 100000]
user_pattern = r"\[PZUser(Mention)?:(\d+):(.+?):PZRT\]"
user_pattern_name = r"\3"


def init(api_base):
    global api
    api = api_base


def handle_root(sender_id: int):
    col = db.col("phizone-bindings")
    if col.count_documents({"qq": sender_id}, limit=1):
        user_id = col.find_one({"qq": sender_id}).get("user_id")
        info = requests.get(f"{api}/users/{user_id}").json()
        return [
            text(
                f"""\
            {get_greeting()}，{info["data"]["userName"]}！
            用户 ID：{info["data"]["id"]}
            等级：{get_user_level(info["data"]["experience"])}
            经验值：{info["data"]["experience"]:,d}
            RKS：{info["data"]["rks"]:.3f}
            关注数：{info["data"]["followeeCount"]}
            粉丝数：{info["data"]["followerCount"]}
            
            /phizone pb|b19 [用户 ID] - 查询个人最佳
            /phizone unbind - 解绑 PhiZone 账号
            /phizone chartsearch|search|cs|sc|s <关键词> - 搜索谱面
            /phizone chartquery|chartinfo|query|info|cq|qc|q|i <谱面 ID> - 查询特定谱面
            /phizone randomchart|random|rc|r - 获取随机谱面
            """
            )
        ]
    return [
        text(
            f"""\
        /phizone pb|b19 [用户 ID] - 查询个人最佳
        /phizone bind <用户 ID> - 绑定 PhiZone 账号
        /phizone unbind - 解绑 PhiZone 账号
        /phizone chartsearch|search|cs|sc|s <关键词> - 搜索谱面
        /phizone chartquery|chartinfo|query|info|cq|qc|q|i <谱面 ID> - 查询特定谱面
        /phizone randomchart|random|rc|r - 获取随机谱面
        """
        )
    ]


def handle_bind(sender_id: int, args: list[string]):
    col = db.col("phizone-bindings")
    if col.count_documents({"qq": sender_id}, limit=1):
        return [
            text(
                f"""\
            你已绑定 PhiZone 账号（ID：{col.find_one({"qq": sender_id}).get("user_id")}）！
            请先使用 /phizone unbind 解绑！
            """
            )
        ]
    user_id = int(args[0])
    col.insert_one({"user_id": user_id, "qq": sender_id})
    info = requests.get(f"{api}/users/{user_id}").json()
    return [text(f"成功绑定至 PhiZone 账号 {info['data']['userName']}！")]


def handle_unbind(sender_id: int):
    col = db.col("phizone-bindings")
    if not col.count_documents({"qq": sender_id}, limit=1):
        return [text("你已处于解绑状态！")]
    col.delete_one({"qq": sender_id})
    return [text("成功解绑 PhiZone 账号！")]


def handle_personal_bests(sender_id: int, args: list[string]):
    if len(args) == 0:
        col = db.col("phizone-bindings")
        if not col.count_documents({"qq": sender_id}, limit=1):
            return [
                text(
                    """\
                你还未绑定 PhiZone 账号！
                1) 使用 /phizone pb|b19 <用户 ID> 查询特定用户的个人最佳；或
                2) 使用 /phizone bind <用户 ID> 绑定 PhiZone 账号。
                """
                )
            ]

        user_id = col.find_one({"qq": sender_id}).get("user_id")
    else:
        user_id = int(args[0])

    info = requests.get(f"{api}/users/{user_id}").json()
    pb = requests.get(f"{api}/users/{user_id}/personalBests").json()
    phi1 = show_record(pb["data"]["phi1"])
    b19 = "\n".join([show_record(record) for record in pb["data"]["best19"]])
    return [
        text(
            f"{info['data']['userName']} 的个人最佳：\n\nPhi 1：\n{phi1}\n\nBest 19：\n{b19}\n\n本功能长期招募 UI！"
        )
    ]


def handle_search_chart(group_id: int, args: list[string]):
    charts = requests.get(f"{api}/charts?search={' '.join(args)}&perPage=3").json()[
        "data"
    ]
    if len(charts) == 0:
        return [text("找不到谱面。")]
    if len(charts) == 1:
        return process_chart(charts[0], group_id)
    results = "\n\n".join([show_chart(chart, brief=True) for chart in charts])
    return [text(f"找到了以下谱面：\n\n{results}")]


def handle_query_chart(group_id: int, args: list[string]):
    return handle_single_chart(requests.get(f"{api}/charts/{args[0]}"), group_id)


def handle_random_chart(group_id: int):
    return handle_single_chart(requests.get(f"{api}/charts/random"), group_id)


def handle_single_chart(response, group_id: int):
    if response.status_code == 404:
        return [text("找不到谱面。")]
    chart = response.json()["data"]
    return process_chart(chart, group_id)


def process_chart(chart, group_id: int):
    def send_preview():
        preview = get_audio_preview(chart["song"])
        group_send(group_id, [audio(preview if preview else chart["song"]["file"])])

    threading.Thread(target=send_preview).start()
    return [
        text(show_chart(chart)),
        image(
            chart["illustration"]
            if chart["illustration"]
            else chart["song"]["illustration"]
        ),
    ]


def get_audio_preview(song):
    if not song["file"]:
        return None
    content = get_cropped_audio(
        song["file"],
        to_seconds(song["previewStart"]),
        to_seconds(song["previewEnd"]),
    )
    return f"base64://{content}"


def show_record(record):
    return "%s [%s %d] %07d %.2f%% %.3f" % (
        record["chart"]["song"]["title"],
        record["chart"]["level"],
        math.floor(record["chart"]["difficulty"]),
        record["score"],
        record["accuracy"] * 100,
        record["rks"],
    )


def show_chart(chart, brief=False):
    return dedent(
        f"""\
    {chart["song"]["title"]} [{chart["level"]} {chart["difficulty"]}]{" [Ranked]" if chart["isRanked"] else ""}
    曲师：{re.sub(user_pattern, user_pattern_name, chart["song"]["authorName"])}
    画师：{chart["illustrator"] if chart["illustrator"] else chart["song"]["illustrator"]}
    谱师：{re.sub(user_pattern, user_pattern_name, chart["authorName"])}
    物量：{chart["noteCount"]}
    ID：{chart["id"]}
    """
        if brief
        else f"""\
    {chart["song"]["title"]} [{chart["level"]} {math.floor(chart["difficulty"])}]{" [Ranked]" if chart["isRanked"] else ""}
    曲师：{re.sub(user_pattern, user_pattern_name, chart["song"]["authorName"])}
    画师：{chart["illustrator"] if chart["illustrator"] else chart["song"]["illustrator"]}
    谱师：{re.sub(user_pattern, user_pattern_name, chart["authorName"])}
    定数：{chart["difficulty"]:.1f}
    物量：{chart["noteCount"]}
    评分：{chart["rating"]:.2f}（配置 {chart["ratingOnArrangement"]:.2f} / 游玩体验 {chart["ratingOnGameplay"]:.2f} / 视觉效果 {chart["ratingOnVisualEffects"]:.2f} / 创新度 {chart["ratingOnCreativity"]:.2f} / 契合度 {chart["ratingOnConcord"]:.2f} / 印象 {chart["ratingOnImpression"]:.2f}）
    游玩数：{chart["playCount"]}
    点赞数：{chart["likeCount"]}
    创建时间：{convert_time(chart["dateCreated"])}
    更新时间：{convert_time(chart["dateUpdated"])}
    文件更新时间：{convert_time(chart["dateFileUpdated"])}
    标签：{'，'.join([tag["name"] for tag in chart["tags"]])}
    ID：{chart["id"]}
    """
    )


def convert_time(time):
    dt_utc = datetime.fromisoformat(time.split('.')[0])
    local_timezone = pytz.timezone("Asia/Shanghai")
    dt_local = dt_utc.astimezone(local_timezone)
    local_time = dt_local.strftime("%Y-%m-%d %H:%M:%S")
    return local_time


def to_seconds(time_str):
    h, m, s = time_str.split(":")
    return int(h) * 3600 + int(m) * 60 + float(s)


def get_user_level(exp):
    for i in range(len(exp_list) - 1, -1, -1):
        if exp_list[i] <= exp:
            return i
    return -1
