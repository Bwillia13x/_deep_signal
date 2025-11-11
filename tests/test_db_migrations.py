from alembic import command
from alembic.config import Config


def test_alembic_upgrade_downgrade(tmp_path):
    cfg = Config("alembic.ini")
    command.upgrade(cfg, "head")
    command.downgrade(cfg, "base")
    command.upgrade(cfg, "head")
