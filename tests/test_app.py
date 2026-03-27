import json
import tempfile
import threading
import time
import unittest
from http.client import HTTPConnection
from pathlib import Path

import app
from app import BookRepository, BookRequestHandler
from http.server import ThreadingHTTPServer


class BookRepositoryTests(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.repo = BookRepository(Path(self.tempdir.name) / "test.db")

    def tearDown(self):
        self.tempdir.cleanup()

    def test_create_and_get_book(self):
        created = self.repo.create_book({"title": "Dune", "author": "Frank Herbert", "year": 1965, "genre": "Sci-Fi"})
        self.assertIsNotNone(created["id"])

        fetched = self.repo.get_book(created["id"])
        self.assertEqual(fetched["title"], "Dune")
        self.assertEqual(fetched["author"], "Frank Herbert")

    def test_update_and_delete_book(self):
        created = self.repo.create_book({"title": "Old", "author": "A"})
        updated = self.repo.update_book(created["id"], {"title": "New", "author": "B", "year": 2000})
        self.assertEqual(updated["title"], "New")
        self.assertEqual(updated["author"], "B")

        deleted = self.repo.delete_book(created["id"])
        self.assertTrue(deleted)
        self.assertIsNone(self.repo.get_book(created["id"]))


class BookApiIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.repo = BookRepository(Path(self.tempdir.name) / "test.db")

        class Handler(BookRequestHandler):
            pass

        Handler.repository = self.repo
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.port = self.server.server_port
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        time.sleep(0.05)

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=1)
        self.tempdir.cleanup()

    def request(self, method, path, body=None):
        conn = HTTPConnection("127.0.0.1", self.port)
        headers = {"Content-Type": "application/json"}
        data = json.dumps(body) if body is not None else None
        conn.request(method, path, body=data, headers=headers)
        response = conn.getresponse()
        payload = response.read().decode("utf-8")
        conn.close()
        return response.status, json.loads(payload)

    def test_full_crud_flow(self):
        status, created = self.request("POST", "/books", {"title": "1984", "author": "George Orwell", "year": 1949})
        self.assertEqual(status, 201)

        status, listed = self.request("GET", "/books")
        self.assertEqual(status, 200)
        self.assertEqual(len(listed), 1)

        book_id = created["id"]
        status, fetched = self.request("GET", f"/books/{book_id}")
        self.assertEqual(status, 200)
        self.assertEqual(fetched["title"], "1984")

        status, updated = self.request("PUT", f"/books/{book_id}", {"title": "Animal Farm", "author": "George Orwell", "year": 1945})
        self.assertEqual(status, 200)
        self.assertEqual(updated["title"], "Animal Farm")

        status, deleted = self.request("DELETE", f"/books/{book_id}")
        self.assertEqual(status, 200)
        self.assertEqual(deleted["message"], "Book deleted")


if __name__ == "__main__":
    unittest.main()
