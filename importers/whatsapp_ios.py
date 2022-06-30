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

import os
import re

import model
import utilities


ENCRYPTION_ANNOUNCEMENT = "Messages and calls are end-to-end encrypted. No one outside of this chat, not even WhatsApp, can read or listen to them."


def event(directory, date, person, content):
    attachment = re.compile(r"^\<attached: (.+)\>$")
    attachment_match = attachment.match(content)
    if attachment_match:
        attachment_path = os.path.join(directory, attachment_match.group(1))
        return model.Attachment(date=date, person=person, content=attachment_path)
    elif utilities.is_emoji(content):
        return model.Emoji(type=model.EventType.EMOJI, date=date, person=person, content=content)
    elif content == ENCRYPTION_ANNOUNCEMENT:
        return None
    else:
        return model.Message(type=model.EventType.MESSAGE, date=date, person=person, content=utilities.text_to_html(content))


# TODO: Fail gracefully
def parse_structure(lines):
    date = None
    username = None
    content = ""
    expression = re.compile(r"^\[(\d{2}/\d{1,2}/\d{2,4}, \d{2}:\d{2}:\d{2})\] (.+?): (.+)")
    for line in lines:
        line = utilities.remove_control_characters(line)
        match = expression.match(line)
        if match:
            if date is not None:
                yield (date, username, content)
            date = match.group(1)
            username = match.group(2)
            content = match.group(3)
        else:
            content = content + line
    if date is not None:
        yield (date, username, content)


def parse_messages(context, directory, lines):
    for (date, username, content) in parse_structure(lines):
        e = event(directory=directory, date=utilities.parse_date(date), person=context.person(identifier=username), content=content)
        if e is not None:
            yield e


def import_messages(context, media_destination_path, path):
    with utilities.unzip(path) as archive_path:
        chats = os.path.join(archive_path, "_chat.txt")
        with open(chats) as fh:
            events = parse_messages(context=context, directory=archive_path, lines=list(fh.readlines()))
            events = list(utilities.copy_attachments(media_destination_path, events))
    return [model.Session(sources=[path], people=utilities.unique([event.person for event in events] + [context.people.primary]), events=events)]
