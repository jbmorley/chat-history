import uuid

import utilities


class Object(object):

    def __init__(self):
        self.id = str(uuid.uuid4())


class Session(Object):

    def __init__(self, events):
        super().__init__()
        self.events = events

    @property
    def people(self):
        return utilities.unique([event.person for event in self.events])


class Conversation(Object):

    def __init__(self, people, batches):
        super().__init__()
        self.people = people
        self.batches = batches

    @property
    def name(self):
        people = sorted(self.people, key=lambda x: x.name)
        return ", ".join([person.name for person in people if not person.is_primary])

