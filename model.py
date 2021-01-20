import uuid

import utilities


class Session(object):

    def __init__(self, events):
        self.id = str(uuid.uuid4())
        self.events = events

    @property
    def people(self):
        return utilities.unique([event.person for event in self.events])
