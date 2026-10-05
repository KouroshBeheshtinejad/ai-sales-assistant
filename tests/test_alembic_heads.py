from alembic.config import Config
from alembic.script import ScriptDirectory


def test_alembic_has_single_head():
    config = Config("alembic.ini")
    script = ScriptDirectory.from_config(config)
    heads = script.get_heads()

    assert len(heads) == 1, f"Expected a single Alembic head, found {len(heads)}: {heads}"
