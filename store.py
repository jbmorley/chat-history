# Copyright (c) 2021-2022 Jason Morley
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
import json
import logging
import os.path
import sqlite3
import time

import dateutil.parser


class Metadata(object):

    SCHEMA_VERSION = "schema_version"


def create_initial_tables(cursor):
    cursor.execute("""
        CREATE TABLE events (
            id TEXT PRIMARY KEY,
            type TEXT,
            timestamp TIMESTAMP,
            person TEXT NOT NULL,
            content JSON
        )
        """)
    cursor.execute("""
        CREATE TABLE people (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL
        )
        """)


class Cursor(sqlite3.Cursor):

    def add_event(self, event):
        self.execute("INSERT INTO events VALUES (?, ?, ?, ?, ?)",
                     (event.id, event.type.value, event.date, event.person.id, event.json()))

    def add_person(self, person):
        self.execute("INSERT INTO people VALUES (?, ?)",
                     (person.id, person.name))


class Transaction(object):

    def __init__(self, connection, cursor_class=sqlite3.Cursor):
        self.connection = connection
        self.cursor_class = cursor_class

    def __enter__(self):
        self.cursor = self.connection.cursor(self.cursor_class)
        return self.cursor

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is None and exc_val is None and exc_tb is None:
            self.connection.commit()
        else:
            self.connection.rollback()
        self.cursor.close()


class Store(object):

    SCHEMA_VERSION = 1

    MIGRATIONS = {
        1: create_initial_tables,
    }

    def __init__(self, path):
        self.path = path
        self.connection = sqlite3.connect(path)

        # Create the metadata table (used for versioning).
        with Transaction(self.connection) as cursor:
            cursor.execute("CREATE TABLE IF NOT EXISTS metadata (key TEXT NOT NULL PRIMARY KEY, value INTEGER)")

        # Create the initial version if necessary.
        with Transaction(self.connection) as cursor:
            cursor.execute("INSERT INTO metadata VALUES (?, ?)",
                           (Metadata.SCHEMA_VERSION, 0))

        self.migrate()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()

    def migrate(self):
        with Transaction(self.connection) as cursor:
            cursor.execute("SELECT value FROM metadata WHERE key=?",
                           (Metadata.SCHEMA_VERSION, ))
            result = cursor.fetchone()
            schema_version = result[0]
            logging.debug(f"Current schema at version {schema_version}")
            if schema_version >= self.SCHEMA_VERSION:
                return
            for i in range(schema_version + 1, self.SCHEMA_VERSION + 1):
                logging.debug(f"Performing migration to version {i}...")
                self.MIGRATIONS[i](cursor)
            cursor.execute("UPDATE metadata SET value=? WHERE key=?",
                           (self.SCHEMA_VERSION, Metadata.SCHEMA_VERSION))
            logging.debug(f"Updated schema to version {self.SCHEMA_VERSION}")

    def close(self):
        self.connection.close()

    def transaction(self):
        return Transaction(self.connection, cursor_class=Cursor)
