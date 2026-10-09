"""Destructive migration regression, restricted to an explicit disposable _test database."""
import os
import uuid
from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url

url = os.environ["DATABASE_URL_SYNC"]
assert make_url(url).database.endswith("_test"), "Only a disposable _test database is allowed"
root = Path(__file__).resolve().parents[2]
config = Config(str(root / "api/alembic.ini"))
config.set_main_option("script_location", str(root / "api/alembic"))
command.downgrade(config, "base")
command.upgrade(config, "0001")
ids = {name: uuid.uuid4() for name in ("account", "prompt", "run", "result", "webhook", "completed")}
engine = create_engine(url)
with engine.begin() as db:
    db.execute(text("INSERT INTO accounts (id,email) VALUES (:account,'migration@example.com')"), ids)
    db.execute(text("""INSERT INTO prompts (id,text,category,severity,expected_behavior)
                    VALUES (:prompt,'Synthetic test','injection','low','Refuse')"""), ids)
    db.execute(text("""INSERT INTO runs (id,account_id,endpoint_url,headers,status,prompt_count)
                    VALUES (:run,:account,'https://example.com','{"Authorization":"test-only"}','running',1)"""), ids)
    db.execute(text("""INSERT INTO runs (id,account_id,endpoint_url,status,prompt_count,composite_score)
                    VALUES (:completed,:account,'https://example.com','completed',0,0.75)"""), ids)
    db.execute(text("INSERT INTO results (id,run_id,prompt_id,status) VALUES (:result,:run,:prompt,'captured')"), ids)
    db.execute(text("""INSERT INTO webhooks (id,account_id,url,secret_hash)
                    VALUES (:webhook,:account,'https://example.com','test-only-hash')"""), ids)
command.upgrade(config, "head")
with engine.connect() as db:
    run = db.execute(text("SELECT status,headers,failed_count FROM runs WHERE id=:run"), ids).one()
    assert run == ("failed", {}, 1), run
    assert db.execute(text("SELECT status,composite_score FROM runs WHERE id=:completed"), ids).one() == ("completed", 0.75)
    assert db.execute(text("SELECT status FROM results WHERE id=:result"), ids).scalar_one() == "error"
    assert db.execute(text("SELECT is_active FROM webhooks WHERE id=:webhook"), ids).scalar_one() is False
command.check(config)
command.downgrade(config, "0001")
command.upgrade(config, "head")
# Leave a clean migrated database for API tests.
command.downgrade(config, "base")
command.upgrade(config, "head")
print("Migration upgrade, historical preservation, downgrade and re-upgrade passed")
