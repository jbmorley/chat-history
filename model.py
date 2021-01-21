import re
import uuid

import utilities


class Object(object):

    def __init__(self):
        self.id = str(uuid.uuid4())


class Session(Object):

    def __init__(self, people, events):
        super().__init__()
        self.people = people
        self.events = events


class Conversation(Object):

    def __init__(self, people, batches):
        super().__init__()
        self.people = people
        self.batches = batches

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
        return stable_identifier
