# BOOK-API

A lightweight CRUD API for managing books, built with Python standard library modules only (`http.server` + `sqlite3`).

## Features
- Create a book
- Read all books
- Read one book by ID
- Update a book
- Delete a book
- Persistent SQLite storage (`books.db`)

## Run
```bash
python3 app.py
```

Server starts at `http://0.0.0.0:8000`.

## API Endpoints

### Create book
`POST /books`

```json
{
  "title": "Dune",
  "author": "Frank Herbert",
  "year": 1965,
  "genre": "Sci-Fi"
}
```

### List books
`GET /books`

### Get one book
`GET /books/{id}`

### Update book
`PUT /books/{id}`

```json
{
  "title": "Dune Messiah",
  "author": "Frank Herbert",
  "year": 1969,
  "genre": "Sci-Fi"
}
```

### Delete book
`DELETE /books/{id}`

## Run tests
```bash
python3 -m unittest discover -s tests -v
```
