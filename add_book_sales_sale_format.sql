-- Migration: Add sale_format to book_sales so earnings account for digital (and future audiobook) sales
-- Run this script on your PostgreSQL database

ALTER TABLE book_sales
ADD COLUMN IF NOT EXISTS sale_format VARCHAR(20) DEFAULT 'digital';

COMMENT ON COLUMN book_sales.sale_format IS 'Sale type: digital (ebook), audiobook, or bundle; used so earnings include digital and audio sales';
