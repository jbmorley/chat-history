#!/usr/bin/env python3

import argparse
import base64
import collections
import datetime
import enum
import functools
import glob
import logging
import mimetypes
import operator
import os
import pathlib
import random
import re
import shutil
import sys
import tempfile
import uuid
import zipfile

import jinja2
import yaml

from PIL import Image as Img

import importers.msn
import importers.text
import model
import utilities


verbose = '--verbose' in sys.argv[1:] or '-v' in sys.argv[1:]
logging.basicConfig(level=logging.DEBUG if verbose else logging.INFO, format="[%(levelname)s] %(message)s")


ROOT_DIRECTORY = os.path.dirname(os.path.abspath(__file__))
TEMPLATES_DIRECTORY = os.path.join(ROOT_DIRECTORY, "templates")


class Person():

    def __init__(self, name, is_primary):
        self.id = str(uuid.uuid4())
        self.name = name
        self.is_primary = is_primary


class Event(object):

    def __init__(self, date, person):
        self.id = str(uuid.uuid4())
        self.date = date
        self.person = person


class Attachment(Event):

    @property
    def type(self):
        return model.EventType.ATTACHMENT

    def __init__(self, date, person, content):
        assert isinstance(date, datetime.datetime)
        assert isinstance(person, Person)
        assert isinstance(content, str)
        super().__init__(date=date, person=person)
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

    def __init__(self, date, person, content, size):
        super(Image, self).__init__(date=date, person=person, content=content)
        self.size = size

    @property
    def type(self):
        return model.EventType.IMAGE


class Video(Attachment):

    @property
    def type(self):
        return model.EventType.VIDEO


class Configuration(object):

    def __init__(self, path):
        self.path = os.path.abspath(path)
        with open(self.path) as fh:
            self.configuration = yaml.load(fh, Loader=yaml.SafeLoader)
        directory = os.path.dirname(self.path)
        for source in self.configuration["sources"]:
            source["path"] = os.path.join(directory, os.path.expanduser(source["path"]))
        self.configuration["output"] = os.path.join(directory, os.path.expanduser(self.configuration["output"]))


class ImportContext(object):

    def __init__(self, people):
        self.people = people

    def person(self, identifier):
        return self.people.person(identifier=identifier)


ENCRYPTION_ANNOUNCEMENT = "Messages and calls are end-to-end encrypted. No one outside of this chat, not even WhatsApp, can read or listen to them."


def event(directory, date, person, content):
    attachment = re.compile(r"^\<attached: (.+)\>$")
    attachment_match = attachment.match(content)
    if attachment_match:
        attachment_path = os.path.join(directory, attachment_match.group(1))
        return Attachment(date=date, person=person, content=attachment_path)
    elif utilities.is_emoji(content):
        return model.Emoji(type=model.EventType.EMOJI, date=date, person=person, content=content)
    elif content == ENCRYPTION_ANNOUNCEMENT:
        return None
    else:
        return model.Message(type=model.EventType.MESSAGE, date=date, person=person, content=utilities.text_to_html(content))


def parse_structure(lines):
    date = None
    username = None
    content = ""
    expression = re.compile(r"^\[(\d{2}/\d{2}/\d{4}, \d{2}:\d{2}:\d{2})\] (.+?): (.+)")
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


def group_messages(people, messages):
    person = None
    items = []
    for message in messages:
        if person != message.person:
            if items:
                yield model.Batch(date=items[0].date, person=person, messages=items)
            person = message.person
            items = []
        items.append(message)
    if items:
        yield model.Batch(date=items[0].date, person=person, messages=items)


class People(object):

    def __init__(self):
        self.people = {}

    def person(self, identifier):
        if identifier not in self.people:
            r = lambda: random.randint(0,255)
            person = Person(name=identifier, is_primary=False)
            self.people[identifier] = person
        return self.people[identifier]

    @property
    def primary(self):
        for person in self.people.values():
            if not person.is_primary:
                continue
            return person
        raise AssertionError("No primary person.")


def copy_attachments(destination, events):
    for event in events:
        if event.type == model.EventType.ATTACHMENT:
            _, ext = os.path.splitext(event.content)
            basename = str(uuid.uuid4()) + ext
            target = os.path.join(destination, basename)
            logging.debug("Copying '%s'...", event.content)
            shutil.copy(event.content, target)
            yield Attachment(date=event.date,
                             person=event.person,
                             content=basename)
        else:
            yield event


IMAGE_TYPES = [".jpg", ".gif", ".png", ".jpeg"]


def detect_images(directory, events):
    for event in events:
        if event.type == model.EventType.ATTACHMENT:
            _, ext = os.path.splitext(event.content)
            if ext.lower() in IMAGE_TYPES:
                image = Img.open(os.path.join(directory, event.content))
                yield Image(date=event.date,
                            person=event.person,
                            content=event.content,
                            size=image.size)
            else:
                yield event
        else:
            yield event


VIDEO_TYPES = [".mp4", ".mov", ".mpg"]


def detect_videos(events):
    for event in events:
        if event.type == model.EventType.ATTACHMENT:
            _, ext = os.path.splitext(event.content)
            if ext.lower() in VIDEO_TYPES:
                yield Video(date=event.date,
                            person=event.person,
                            content=event.content)
            else:
                yield event
        else:
            yield event


def whatsapp_export(context, media_destination_path, path):
    with utilities.unzip(path) as archive_path:
        chats = os.path.join(archive_path, "_chat.txt")
        with open(chats) as fh:
            events = parse_messages(context=context, directory=archive_path, lines=list(fh.readlines()))
            events = list(copy_attachments(media_destination_path, events))
    return [model.Session(sources=[path], people=utilities.unique([event.person for event in events] + [context.people.primary]), events=events)]


def hash_identifiers(objects):
    return ".".join(sorted([o.id for o in objects]))


def merge_events(events):
    events_copy = [list(e) for e in events]
    result = []
    while True:
        try:
            events_copy = sorted(events_copy, key=lambda x: x[0].date)
        except TypeError as e:
            for events_list in events_copy:
                logging.error(events_list[0])
            raise e
        result.append(events_copy[0].pop(0))
        events_copy = [e for e in events_copy if e]
        if not events_copy:
            break
    return result


def merge_sessions(sessions):
    events = merge_events([session.events for session in sessions])
    sources = functools.reduce(operator.concat, [session.sources for session in sessions], [])
    session = model.Session(sources=sources,
                            people=utilities.unique(functools.reduce(operator.concat,
                                                                     [session.people for session in sessions],
                                                                     [])),
                            events=events)
    return session


def received_files_import(context, media_destination_path, path):
    sessions = []
    for identifier in os.listdir(path):
        user_path = os.path.join(path, identifier)
        if not os.path.isdir(user_path):
            continue
        logging.info("Importing '%s'...", user_path)
        attachments = []
        files = [os.path.join(user_path, p) for p in os.listdir(user_path) if os.path.isfile(os.path.join(user_path, p))]
        for f in files:
            date = utilities.ensure_timezone(datetime.datetime.fromtimestamp(os.path.getmtime(f)))
            person = context.person(identifier=identifier)
            attachment = Attachment(date, person, f)
            attachments.append(attachment)
        if attachments:
            events = list(copy_attachments(media_destination_path, attachments))
            events = sorted(events, key=lambda x: x.date)
            sessions.append(model.Session(sources=[path],
                                          people=utilities.unique([event.person for event in events] + [context.people.primary]),
                                          events=events))
    return sessions


IMPORTERS = {
    "whatsapp_ios": whatsapp_export,
    "received_files": received_files_import,
    "msn_messenger": importers.msn.msn_messenger,
    "text_archive": importers.text.text_archive,
}


def main():
    parser = argparse.ArgumentParser(description="Parse chat logs and generate HTML.")
    parser.add_argument("--verbose", "-v", action="store_true", default=False, help="verbose logging")
    parser.add_argument("configuration", help="configuration file")
    options = parser.parse_args()

    configuration = Configuration(options.configuration)
    if os.path.exists(configuration.configuration["output"]):
        shutil.rmtree(configuration.configuration["output"])
    os.makedirs(configuration.configuration["output"])

    people = People()
    for person in configuration.configuration["people"]:
        p = Person(name=person["name"],
                   is_primary=person["primary"] if "primary" in person else False)
        for identity in person["identities"]:
            people.people[identity] = p

    # Run all the importers.
    sessions = []
    conversations = []
    for source in configuration.configuration["sources"]:
        context = ImportContext(people=people)
        importer = IMPORTERS[source["format"]]
        paths = utilities.glob(".", source["path"])
        if not paths:
            logging.error("Unable to find anything to import for '%s'.", source["path"])
            exit()
        for path in paths:
            logging.info("Importing '%s'...", path)
            for session in importer(context, configuration.configuration["output"], path):
                events = detect_images(configuration.configuration["output"], session.events)
                events = list(detect_videos(events))
                sessions.append(model.Session(sources=session.sources, people=session.people, events=events))

    # Merge conversations.
    threads = collections.defaultdict(list)
    for session in sessions:
        threads[hash_identifiers(session.people)].append(session)
    sessions = [merge_sessions(sessions) for sessions in threads.values()]

    # Generate conversations.
    # TODO: Consider doing this at render time.
    for session in sessions:
        batches = list(group_messages(session.people, session.events))
        conversation = model.Conversation(sources=session.sources, people=session.people, batches=batches)
        conversations.append(conversation)

    # Sort the conversations by name.
    conversations = sorted(conversations, key=lambda x: x.name)

    environment = jinja2.Environment(loader=jinja2.FileSystemLoader(TEMPLATES_DIRECTORY))
    with utilities.chdir(configuration.configuration["output"]):
        conversation_template = environment.get_template("conversation.html")
        index_template = environment.get_template("index.html")
        with open("index.html", "w") as fh:
            fh.write(conversation_template.render(conversations=conversations, EventType=model.EventType))
        for conversation in conversations:
            with open(f"{conversation.stable_identifier}.html", "w") as fh:
                fh.write(conversation_template.render(conversations=conversations, conversation=conversation, EventType=model.EventType))

if __name__ == '__main__':
    main()
