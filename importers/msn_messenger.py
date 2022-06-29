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

import logging
import os
import re

import lxml.etree

import emoticons
import utilities
import model


def import_messages(context, media_destination_path, path):
    basename, _ = os.path.splitext(os.path.basename(path))
    default_person = context.person(identifier=basename)

    sessions = []
    with open(path) as fh:
        try:
            log = lxml.etree.fromstring(fh.read())
        except lxml.etree.XMLSyntaxError:
            logging.error("Failed to parse XML")
            return []
        events = []
        for message in log.xpath('Message'):
            # lxml.etree.dump(message)
            date = utilities.parse_date(message.xpath('@DateTime')[0])
            text = message.xpath('Text/text()')[0]
            identities = [message.xpath('From/User/@LogonName')[0],
                          message.xpath('From/User/@FriendlyName')[0]]
            identity = str(next(s for s in identities if s))
            events.append(model.Message(type=model.EventType.MESSAGE,
                                        date=date,
                                        person=context.person(identifier=identity),
                                        content=utilities.text_to_html(emoticons.detect(text))))
        if events:
            sessions.append(model.Session(sources=[path],
                                          people=utilities.unique([event.person for event in events] + [context.people.primary] + [default_person]),
                                          events=events))
    return sessions
