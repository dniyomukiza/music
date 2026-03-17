-- Migration: Add audiobook_chapters table for per-chapter audiobook playback
-- Listeners can pick and play any chapter when they buy an audiobook
-- Run this if db.create_all() doesn't create the table automatically

-- PostgreSQL
CREATE TABLE IF NOT EXISTS audiobook_chapters (
    id SERIAL PRIMARY KEY,
    book_project_id INTEGER NOT NULL REFERENCES book_projects(id) ON DELETE CASCADE,
    chapter_number INTEGER NOT NULL,
    title VARCHAR(300) NOT NULL,
    audio_file_path VARCHAR(500) NOT NULL,
    duration_seconds INTEGER DEFAULT 0,
    book_chapter_id INTEGER REFERENCES book_chapters(id) ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS ix_audiobook_chapters_book_project_id ON audiobook_chapters(book_project_id);
