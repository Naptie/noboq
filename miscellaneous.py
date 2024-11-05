from datetime import datetime


def get_greeting():
    current_hour = datetime.now().hour

    if 0 <= current_hour < 6:
        return "凌晨好"
    elif current_hour < 10:
        return "早上好"
    elif current_hour < 12:
        return "上午好"
    elif current_hour < 14:
        return "中午好"
    elif current_hour < 18:
        return "下午好"
    else:
        return "晚上好"
