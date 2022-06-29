# Copyright (c) 2021 Jason Morley
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

import datetime
import logging
import os

import model
import utilities


def import_messages(context, media_destination_path, path):
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
            attachment = model.Attachment(date, person, f)
            attachments.append(attachment)
        if attachments:
            events = list(utilities.copy_attachments(media_destination_path, attachments))
            events = sorted(events, key=lambda x: x.date)
            sessions.append(model.Session(sources=[path],
                                          people=utilities.unique([event.person for event in events] + [context.people.primary]),
                                          events=events))
    return sessions
