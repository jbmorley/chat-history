import logging
import os

import pyparsing as pp

from pyparsing import Combine, Group, Keyword, LineEnd, OneOrMore, Suppress, Word, ZeroOrMore

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
            for participant in session["participants"]:
                pass
                # print(participant["name"], participant["email"])
            events = []
            for message in session["messages"]:
                date = utilities.parse_date(session["start"] + " " + message["time"])
                # print(date, message["user"], message["content"])
                events.append(model.Message(type=model.EventType.MESSAGE,
                                            date=date,
                                            person=context.person(identifier=message["user"]),
                                            content=utilities.text_to_html(message["content"])))
            if events:
                results.append(model.Session(sources=[path],
                                             people=utilities.unique([event.person for event in events] + [context.people.primary]),
                                             events=events))

    except pp.ParseException:
        logging.error("Unable to parse '%s'.", path)

    return results
