import logging
import os
import re

import lxml.etree

import utilities
import model


EMOTICONS = {

    ":-)": "🙂",
    ":)": "🙂",

    ":-D": "😀",
    ":d": "😀",

    ":-O": "😮",
    ":o": "😮",

    ":-P": "😛",
    ":p": "😛",

    ";-)": "😉",
    ";)": "😉",

    ":-S": "😕",
    ":s": "😕",

    ":-|": "😐",
    ":|": "😐",

    ":'(": "😢",

    ":-$": "😊",
    ":$": "😊",

    "({)": "🤗",
    "(})": "🤗",
}

EMOTICON_EXPRESSIONS = {re.compile(re.escape(string), re.IGNORECASE): emoji for (string, emoji) in EMOTICONS.items()}


def replace_emoticons(text):
    for expression, emoji in EMOTICON_EXPRESSIONS.items():
        text = expression.sub(emoji, text)
    return text


def msn_messenger_import(context, media_destination_path, path):
    # for f in os.listdir(path):
        # logging.info(f)

    basename, _ = os.path.splitext(os.path.basename(path))
    default_person = context.person(identifier=basename)

    sessions = []
    with open(path) as fh:
        log = lxml.etree.fromstring(fh.read())
        events = []
        for message in log:
            from_logon_name = message.xpath('From/User/@LogonName')[0]
            from_friendly_name = message.xpath('From/User/@FriendlyName')[0]
            date = utilities.parse_date(message.xpath('@DateTime')[0])
            text = message.xpath('Text/text()')[0]

            identities = [message.xpath('From/User/@LogonName')[0],
                          message.xpath('From/User/@FriendlyName')[0]]
            identity = next(s for s in identities if s)
            events.append(model.Message(type=model.EventType.MESSAGE,
                                        date=date,
                                        person=context.person(identifier=identity),
                                        content=utilities.text_to_html(replace_emoticons(text))))
        if events:
            sessions.append(model.Session(people=utilities.unique([event.person for event in events] + [context.people.primary] + [default_person]),
                                          events=events))
        # lxml.etree.dump(log)
    return sessions
