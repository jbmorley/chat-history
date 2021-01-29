import collections
import enum
import re
import uuid

import utilities
import yaml


Batch = collections.namedtuple('Batch', ['date', 'person', 'messages'])
Message = collections.namedtuple('Message', ['type', 'date', 'person', 'content'])
Emoji = collections.namedtuple('Emoji', ['type', 'date', 'person', 'content'])


class EventType(enum.Enum):
    MESSAGE = "message"
    EMOJI = "emoji"
    ATTACHMENT = "attachment"
    IMAGE = "image"
    VIDEO = "video"


class Object(object):

    def __init__(self):
        self.id = str(uuid.uuid4())


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

    @property
    def stable_identifier(self):
        people = sorted(self.people, key=lambda x: x.name)
        stable_identifier = "-".join([person.name.lower() for person in people if not person.is_primary])
        stable_identifier = utilities.remove_control_characters(stable_identifier)
        stable_identifier = stable_identifier.strip()
        stable_identifier = re.sub(r"[\\\/,\s\+\- ]+", "-", stable_identifier)
        stable_identifier = re.sub(r"\-+", "-", stable_identifier)
        return stable_identifier[:100]
