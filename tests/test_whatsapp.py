#!/usr/bin/env python3

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

import datetime
import unittest

import pytz

import importers.whatsapp_ios
import model


class TestWhatsApp(unittest.TestCase):

    def test_parse_message(self):
        context = model.ImportContext(people=model.People())
        messages = importers.whatsapp_ios.parse_messages(context, ".", ["[29/06/2022, 15:25:18] Pavlos Vinieratos: hey hey"])
        messages = list(messages)
        self.assertEqual(len(messages), 1)
        message = messages[0]
        self.assertEqual(message.date, datetime.datetime(2022, 6, 29, 15, 25, 18).replace(tzinfo=pytz.utc))
        self.assertEqual(message.content, "<p>hey hey</p>")

    def test_parse_message_short_dates(self):
        context = model.ImportContext(people=model.People())
        messages = importers.whatsapp_ios.parse_messages(context, ".", ["[29/6/22, 17:26:11] Jason Morley: Swwwwweeeeeeet."])
        messages = list(messages)
        self.assertEqual(len(messages), 1)
        message = messages[0]
        self.assertEqual(message.date, datetime.datetime(2022, 6, 29, 17, 26, 11).replace(tzinfo=pytz.utc))
        self.assertEqual(message.content, "<p>Swwwwweeeeeeet.</p>")


if __name__ == '__main__':
    unittest.main()
