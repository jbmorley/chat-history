import re


EMOTICONS = {

    # Smile
    ":-)": "🙂",
    ":)": "🙂",

    # Open-mouthed
    ":-D": "😀",
    ":d": "😀",

    # Surprised
    ":-O": "😮",
    ":o": "😮",

    # Tongue out
    ":-P": "😛",
    ":p": "😛",

    # Wink
    ";-)": "😉",
    ";)": "😉",

    # Sad
    ":-(": "🙁",
    ":(": "🙁",

    ":-S": "😕",
    ":s": "😕",

    ":-|": "😐",
    ":|": "😐",

    ":'(": "😢",

    ":-$": "😊",
    ":$": "😊",

    "(H)": "😎",

    # Party
    "<:o)": "🥳",

    # Sleepy
    "|-)": "😴",

    "(N)": "👎🏻",

    "({)": "🤗",
    "(})": "🤗",

    "(T)": "📞",

    "(I)": "💡",

    "(8)": "🎵",

    # Sleeping half-moon
    "(S)": "🌘",
}

EMOTICON_EXPRESSIONS = {re.compile(re.escape(string), re.IGNORECASE): emoji for (string, emoji) in EMOTICONS.items()}


def detect(text):
    for expression, emoji in EMOTICON_EXPRESSIONS.items():
        text = expression.sub(emoji, text)
    return text
