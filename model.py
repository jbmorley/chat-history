# Copyright (c) 2021-2024 Jason Morley
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

import collections
import datetime
import enum
import json
import mimetypes
import re
import uuid

import utilities
import yaml


Batch = collections.namedtuple('Batch', ['date', 'person', 'events'])
Emoji = collections.namedtuple('Emoji', ['type', 'date', 'person', 'content'])


class ImportContext(object):

    def __init__(self, people):
        self.people = people

    def person(self, identifier):
        return self.people.person(identifier=identifier)


class People(object):

    def __init__(self):
        self.people = {}

    def person(self, identifier):
        if identifier not in self.people:
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


class EventType(enum.Enum):
    MESSAGE = "message"
    EMOJI = "emoji"
    ATTACHMENT = "attachment"
    IMAGE = "image"
    VIDEO = "video"


class Object(object):

    def __init__(self):
        self.id = str(uuid.uuid4())


class Person(Object):

    def __init__(self, name, is_primary):
        super().__init__()
        self.name = name
        self.is_primary = is_primary

    def __hash__(self):
        return hash(self.id)


class Session(Object):

    def __init__(self, sources, people, events):
        super().__init__()
        self.sources = sources
        self.people = people
        self.events = events


class Conversation(Object):

    def __init__(self, sources, people, batches):
        super().__init__()
        self.sources = sources
        self.people = people
        self.batches = batches

    # TODO: Ultimately we should use the person instead to get the configuration.
    @property
    def configuration(self):
        return yaml.dump([{"name": self.name,
                           "identities": [person.name for person in self.people if not person.is_primary]}],
                         sort_keys=False)

    @property
    def name(self):
        people = sorted(self.people, key=lambda x: x.name)
        return ", ".join([person.name for person in people if not person.is_primary])


class Event(object):

    def __init__(self, date, person):
        self.id = str(uuid.uuid4())
        self.date = date
        self.person = person

    def json(self):
        return json.dumps({
            "type": self.type.value,
            "date": self.date.isoformat(),
            "person": self.person.id,
        })


class Message(Event):

    def __init__(self, type, date, person, content):
        super().__init__(date, person)
        self.type = type
        self.content = content

    def json(self):
        return json.dumps({
            "type": self.type.value,
            "date": self.date.isoformat(),
            "person": self.person.id,
            "content": self.content
        })


class Attachment(Event):

    @property
    def type(self):
        return EventType.ATTACHMENT

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
        return EventType.IMAGE


class Video(Attachment):

    @property
    def type(self):
        return EventType.VIDEO
