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

import pyparsing as pp

from pyparsing import Combine, Group, Keyword, LineEnd, OneOrMore, Suppress, Word, ZeroOrMore

import emoticons
import model
import utilities


class Characters(object):

    def __init__(self, string):
        self.string = string

    def __str__(self):
        return self.string

    def __iter__(self):
        return self.string.__iter__()

    def __len__(self):
        return self.string.__len__()

    def __getitem__(self, index):
        return self.string.__getitem__(index)

    def __add__(self, obj):
        if isinstance(obj, str):
            return Characters(self.string + obj)
        elif isinstance(obj, Characters):
            return Characters(self.string + obj.string)
        else:
            raise AssertionError("Unsupported type.")

    def __sub__(self, obj):
        if isinstance(obj, str):
            return Characters("".join(set(self.string) - set(obj)))
        elif isinstance(obj, Characters):
            return Characters("".join(set(self.string) - set(obj.string)))
        else:
            raise AssertionError("Unsupported type.")


def read(path):
    with open(path, "rb") as fh:
        content = fh.read()
        for encoding in ['utf-8', 'utf-16', 'iso-8859-1']:
            try:
                return content.decode(encoding)
            except UnicodeDecodeError:
                pass
    raise AssertionError("Unable to determine the encoding")


def is_partial(participant):
    return participant.startswith("...")


class ParticipantMap(object):

    def __init__(self, participants):
        self.participants = {}
        for participant in participants:
            self.participants[participant["name"].strip()] = participant["email"]

    def lookup(self, user):
        try:
            return self.participants[user]
        except KeyError as e:

            # Some users are truncated with an ellipsis.
            if user.endswith(".."):
                user = user[:-2]

            # Before we do anything too clever, we see if any of the participants have
            # names that begin with the partial user.
            for participant in self.participants.keys():
                if participant.startswith(user):
                    return self.participants[participant]

            # Assuming that failed, we need to do the same, slowly trimming down the user and
            # only matching against known partial participants.
            while user:
                user = user[1:]
                for participant in [participant for participant in self.participants.keys() if participant.startswith("...")]:
                    if participant[3:].startswith(user):
                        return self.participants[participant]

            raise e



def text_archive(context, media_destination_path, path):

    content = read(path)
    # content = utilities.remove_control_characters(content)

    LINE_END = Suppress(LineEnd())
    PIPE = Suppress("|")

    TIME = Combine(Word(pp.nums) + ":" + Word(pp.nums) + ":" + Word(pp.nums))
    USERNAME = Combine(OneOrMore(Word(pp.alphas.replace(":", "") + ".") | pp.White()))
    INDENTATION = pp.White(' ', min=8).setParseAction(pp.replaceWith(" "))
    SENTENCE = Combine(OneOrMore(Word(pp.printables) | " " | "\t"))
    CONTENT = Combine(SENTENCE +
                      Suppress(Word("\r\n")) +
                      ZeroOrMore(INDENTATION + SENTENCE + Suppress(Word("\r\n"))))
    MESSAGE = Group(Suppress("[") + TIME.setResultsName("time") + Suppress("]") +
                    USERNAME.setResultsName("user") + Suppress(":") +
                    CONTENT.setResultsName("content"))

    HEADER_SEPARATOR = Suppress(Keyword(".--------------------------------------------------------------------.") + LINE_END)

    SESSION_DATE = Combine(Word(pp.nums) + pp.White(" ") + Word(pp.alphas) + pp.White(" ") + Word(pp.nums))
    SESSION_START = (PIPE +
                     Suppress(Keyword("Session Start")) + Suppress(":") + SESSION_DATE.setResultsName("start") +
                     PIPE +
                     LINE_END)

    PARTICIPANT_NAME = Word(Characters(pp.printables) + " " - "(")
    PARTICIPANT_EMAIL = Word(pp.printables.replace(")", ""))
    PARTICIPANT_LINE = Group(PIPE +
                             PARTICIPANT_NAME.setResultsName("name") +
                             Suppress("(") + PARTICIPANT_EMAIL.setResultsName("email") + Suppress(")") +
                             PIPE +
                             LINE_END)
    PARTICIPANTS = PIPE + Suppress(Keyword("Participants")) + Suppress(":") + PIPE + LINE_END + OneOrMore(PARTICIPANT_LINE)

    HEADER = (HEADER_SEPARATOR +
              SESSION_START +
              PARTICIPANTS.setResultsName("participants") +
              HEADER_SEPARATOR)

    SESSION = Group((HEADER +
                    Group(OneOrMore(MESSAGE)).setResultsName("messages")))

    parser = OneOrMore(SESSION)

    try:
        results = []
        sessions = parser.parseString(content)

        for session in sessions:
            # print(session["start"])

            participant_map = ParticipantMap(participants=session["participants"])

            events = []
            for message in session["messages"]:
                date = utilities.parse_date(session["start"] + " " + message["time"])
                user = message["user"]

                if user == 'The following message could not be delivered to all\r\n           recipients':
                    continue

                identifier = user
                try:
                    identifier = participant_map.lookup(user)
                except KeyError:
                    logging.debug("Unable to find email for user '%s'", user)

                events.append(model.Message(type=model.EventType.MESSAGE,
                                            date=date,
                                            person=context.person(identifier=identifier),
                                            content=utilities.text_to_html(emoticons.detect(message["content"]))))
            if events:
                results.append(model.Session(sources=[path],
                                             people=utilities.unique([event.person for event in events] + [context.people.primary]),
                                             events=events))

    except pp.ParseException:
        logging.error("Unable to parse '%s'.", path)

    return results
