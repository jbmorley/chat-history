#!/usr/bin/env python3

import argparse
import base64
import collections
import enum
import mimetypes
import os
import pathlib
import random
import re
import shutil
import uuid

import dateutil.parser
import jinja2
import yaml

import utilities


class EventType(enum.Enum):
    MESSAGE = "message"
    EMOJI = "emoji"
    ATTACHMENT = "attachment"
    IMAGE = "image"
    VIDEO = "video"


ROOT_DIRECTORY = os.path.dirname(os.path.abspath(__file__))
TEMPLATES_DIRECTORY = os.path.join(ROOT_DIRECTORY, "templates")


Batch = collections.namedtuple('Batch', ['person', 'messages'])  # TODO: Rename to events?
Person = collections.namedtuple('Person', ['name', 'is_primary'])

Message = collections.namedtuple('Message', ['type', 'date', 'username', 'content'])
Emoji = collections.namedtuple('Emoji', ['type', 'date', 'username', 'content'])
Attachment = collections.namedtuple('Attachment', ['type', 'date', 'username', 'content'])
Image = collections.namedtuple('Image', ['type', 'date', 'username', 'content', 'mimetype'])
Video = collections.namedtuple('Video', ['type', 'date', 'username', 'content', 'mimetype'])


class Attachment(object):

    @property
    def type(self):
        return EventType.ATTACHMENT

    def __init__(self, date, username, content):
        self.date = date
        self.username = username
        self.content = content

    @property
    def mimetype(self):
        return mimetypes.guess_type(self.content)[0]

    @property
    def base64_data(self):
        with open(self.content, "rb") as fh:
            return base64.b64encode(fh.read()).decode('ascii')

    @property
    def data_url(self):
        return f"data:{self.mimetype};base64," + self.base64_data


class Image(Attachment):

    @property
    def type(self):
        return EventType.IMAGE



class Video(Attachment):

    @property
    def type(self):
        return EventType.VIDEO


class Configuration(object):

    def __init__(self, path):
        self.path = os.path.abspath(path)
        with open(self.path) as fh:
            self.configuration = yaml.load(fh, Loader=yaml.SafeLoader)
        directory = os.path.dirname(self.path)
        for source in self.configuration["sources"]:
            source["path"] = os.path.join(directory, source["path"])
        self.configuration["output"] =os.path.join(directory, self.configuration["output"])


def event(directory, date, username, content):
    attachment = re.compile(r"^\<attached: (.+)\>$")
    attachment_match = attachment.match(content)
    if attachment_match:
        attachment_path = os.path.join(directory, attachment_match.group(1))
        return Attachment(date=date, username=username, content=attachment_path)
    elif utilities.is_emoji(content):
        return Emoji(type=EventType.EMOJI, date=date, username=username, content=content)
    else:
        return Message(type=EventType.MESSAGE, date=date, username=username, content=utilities.text_to_html(content))


def parse_structure(lines):
    date = None
    username = None
    content = ""
    expression = re.compile(r"^\[(\d{2}/\d{2}/\d{4}, \d{2}:\d{2}:\d{2})\] (.+?): (.+)")
    for line in lines:
        line = line.replace("\u200e", "")  # TODO: Attachments have a non-printing character that breaks the regex.
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


def parse_messages(directory, lines):
    for (date, username, content) in parse_structure(lines):
        yield event(directory=directory, date=dateutil.parser.parse(date), username=username, content=content)


def group_messages(people, messages):
    username = None
    items = []
    for message in messages:
        if username != message.username:
            if items:
                yield Batch(person=people.person(username=username), messages=items)
            username = message.username
            items = []
        items.append(message)
    if items:
        yield Batch(person=people.person(username=username), messages=items)


class People(object):

    def __init__(self):
        self.people = {}

    def person(self, username):
        if username not in self.people:
            r = lambda: random.randint(0,255)
            person = Person(name=username, is_primary=False)
            self.people[username] = person
        return self.people[username]


def copy_attachments(destination, events):
    for event in events:
        if event.type == EventType.ATTACHMENT:
            print(f"Copying '{event.content}'...")
            _, ext = os.path.splitext(event.content)
            basename = str(uuid.uuid4()) + ext
            shutil.copy(event.content, os.path.join(destination, basename))
            yield Attachment(date=event.date,
                             username=event.username,
                             content=basename)
        else:
            yield event


IMAGE_TYPES = [".jpg", ".gif"]


def detect_images(events):
    for event in events:
        if event.type == EventType.ATTACHMENT:
            _, ext = os.path.splitext(event.content)
            if ext in IMAGE_TYPES:
                yield Image(date=event.date,
                            username=event.username,
                            content=event.content)
            else:
                yield event
        else:
            yield event


VIDEO_TYPES = [".mp4", ".mov"]


def detect_videos(events):
    for event in events:
        if event.type == EventType.ATTACHMENT:
            _, ext = os.path.splitext(event.content)
            if ext in VIDEO_TYPES:
                yield Video(date=event.date,
                            username=event.username,
                            content=event.content)
            else:
                yield event
        else:
            yield event


def main():
    parser = argparse.ArgumentParser(description="Parse chat logs and generate HTML.")
    parser.add_argument("configuration", help="configuration file")
    options = parser.parse_args()

    configuration = Configuration(options.configuration)
    if os.path.exists(configuration.configuration["output"]):
        shutil.rmtree(configuration.configuration["output"])
    os.makedirs(configuration.configuration["output"])

    people = People()
    for person in configuration.configuration["people"]:
        people.people[person["identities"][0]] = Person(name=person["name"],
                                                        is_primary=person["primary"] if "primary" in person else False)

    for source in configuration.configuration["sources"]:
        chats = os.path.join(source["path"], "_chat.txt")
        with open(chats) as fh:
            events = parse_messages(directory=source["path"], lines=list(fh.readlines()))

    events = copy_attachments(configuration.configuration["output"], events)
    events = detect_images(events)
    events = detect_videos(events)
    batches = group_messages(people, events)

    environment = jinja2.Environment(loader=jinja2.FileSystemLoader(TEMPLATES_DIRECTORY))
    template = environment.get_template("messages.html")
    with utilities.chdir(configuration.configuration["output"]):
        with open("index.html", "w") as fh:
            fh.write(template.render(conversation=list(batches), EventType=EventType))


if __name__ == '__main__':
    main()
