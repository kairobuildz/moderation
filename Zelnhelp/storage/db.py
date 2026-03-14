import aiosqlite, os
DB_PATH = os.path.join(os.path.dirname(__file__), "vexus.db")
INIT_SQL = """
CREATE TABLE IF NOT EXISTS warnings(
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 guild_id TEXT NOT NULL,
 user_id TEXT NOT NULL,
 mod_id TEXT NOT NULL,
 reason TEXT NOT NULL,
 created_at INTEGER NOT NULL
);
"""
async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.executescript(INIT_SQL); await db.commit()
async def add_warn(guild_id, user_id, mod_id, reason, created_at):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("INSERT INTO warnings (guild_id,user_id,mod_id,reason,created_at) VALUES (?,?,?,?,?)",
                         (str(guild_id),str(user_id),str(mod_id),reason,created_at)); await db.commit()
async def get_warns(guild_id, user_id):
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("SELECT id,mod_id,reason,created_at FROM warnings WHERE guild_id=? AND user_id=? ORDER BY created_at ASC",
                               (str(guild_id),str(user_id))); return await cur.fetchall()
async def remove_warn(guild_id, user_id, index):
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("SELECT id FROM warnings WHERE guild_id=? AND user_id=? ORDER BY created_at ASC",
                               (str(guild_id),str(user_id))); rows = await cur.fetchall()
        if index<1 or index>len(rows): return False
        await db.execute("DELETE FROM warnings WHERE id=?", (rows[index-1][0],)); await db.commit(); return True
async def clear_warns(guild_id, user_id):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM warnings WHERE guild_id=? AND user_id=?", (str(guild_id),str(user_id))); await db.commit()
