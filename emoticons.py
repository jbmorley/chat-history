# Copyright (c) 2021-2022 Jason Morley
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

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
