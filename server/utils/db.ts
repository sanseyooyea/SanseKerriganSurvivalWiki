import Database from 'better-sqlite3'
import { join } from 'path'

let db: Database.Database | null = null

export function getDb(): Database.Database {
  if (db) return db
  const dbPath = join(process.cwd(), 'data', 'wiki.db')
  db = new Database(dbPath)
  db.pragma('journal_mode = WAL')
  db.pragma('foreign_keys = ON')
  initSchema(db)
  return db
}

function initSchema(db: Database.Database) {
  db.exec(`
    CREATE TABLE IF NOT EXISTS users (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      username TEXT UNIQUE NOT NULL,
      password_hash TEXT NOT NULL,
      role TEXT NOT NULL DEFAULT 'user',
      handle TEXT DEFAULT '',
      created_at TEXT DEFAULT (datetime('now'))
    );

    CREATE TABLE IF NOT EXISTS wiki_pages (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      slug TEXT UNIQUE NOT NULL,
      title TEXT NOT NULL,
      content TEXT NOT NULL DEFAULT '',
      category TEXT DEFAULT 'general',
      updated_by INTEGER REFERENCES users(id),
      updated_at TEXT DEFAULT (datetime('now'))
    );

    CREATE TABLE IF NOT EXISTS wiki_revisions (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      page_id INTEGER NOT NULL REFERENCES wiki_pages(id),
      title TEXT NOT NULL,
      content TEXT NOT NULL,
      edited_by INTEGER REFERENCES users(id),
      created_at TEXT DEFAULT (datetime('now'))
    );

    CREATE TABLE IF NOT EXISTS comments (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      page_slug TEXT NOT NULL,
      user_id INTEGER NOT NULL REFERENCES users(id),
      content TEXT NOT NULL,
      created_at TEXT DEFAULT (datetime('now'))
    );

    CREATE TABLE IF NOT EXISTS class_overrides (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      class_id INTEGER UNIQUE NOT NULL,
      data TEXT NOT NULL DEFAULT '{}',
      updated_by INTEGER REFERENCES users(id),
      updated_at TEXT DEFAULT (datetime('now'))
    );

    -- 用户建议/反馈：category(feature/bug/data/other)，
    -- status(pending待处理/accepted已采纳/rejected不采纳/done已完成)
    CREATE TABLE IF NOT EXISTS feedback (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      user_id INTEGER NOT NULL REFERENCES users(id),
      category TEXT NOT NULL DEFAULT 'feature',
      title TEXT NOT NULL,
      content TEXT NOT NULL DEFAULT '',
      status TEXT NOT NULL DEFAULT 'pending',
      admin_note TEXT NOT NULL DEFAULT '',
      created_at TEXT DEFAULT (datetime('now')),
      updated_at TEXT DEFAULT (datetime('now'))
    );

    -- 点赞：一个用户对一条建议至多一票
    CREATE TABLE IF NOT EXISTS feedback_votes (
      feedback_id INTEGER NOT NULL REFERENCES feedback(id) ON DELETE CASCADE,
      user_id INTEGER NOT NULL REFERENCES users(id),
      created_at TEXT DEFAULT (datetime('now')),
      PRIMARY KEY (feedback_id, user_id)
    );
  `)
}
