import os

from alembic import command
from alembic.config import Config
from alembic.runtime.environment import EnvironmentContext
from alembic.script import ScriptDirectory
from depot.manager import DepotManager
from pyramid import testing
from sqlalchemy import text
from sqlalchemy.engine import Engine
import transaction

from tracim_backend.fixtures.content import Content as ContentFixture
from tracim_backend.fixtures.users_and_groups import Base as BaseFixture
from tracim_backend.lib.utils.logger import logger
from tracim_backend.models.meta import DeclarativeBase
from tracim_backend.models.setup_models import *  # noqa: F403,F401
from tracim_backend.tests import TEST_CONFIG_FILE_PATH
from tracim_backend.tests import BaseTest

TEST_MIGRATION_SCRIPT_LOCATION = os.environ.get("TEST_MIGRATION_SCRIPT_LOCATION")


def get_revision(
    config: Config, engine: Engine, script: ScriptDirectory, revision_type="current"
) -> str:
    """
    Helper to get revision id
    """
    with engine.connect() as conn:
        with EnvironmentContext(config, script) as env_context:
            env_context.configure(conn, version_table="migrate_version")
            if revision_type == "head":
                revision = env_context.get_head_revision()
            else:
                migration_context = env_context.get_context()
                revision = migration_context.get_current_revision()
    return revision


class TestMigration(BaseTest):
    # Test for alembic migration
    # mostly inspired by alembic-verify but with requirement for alembic_verify

    fixtures = [BaseFixture, ContentFixture]
    config_uri = TEST_CONFIG_FILE_PATH
    config_section = "migration_test"

    def tearDown(self) -> None:
        logger.debug(self, "TearDown Test...")

        self.session.rollback()
        self.session.close_all()
        transaction.abort()
        DeclarativeBase.metadata.drop_all(self.engine)
        sql = text("DROP TABLE IF EXISTS migrate_version;")
        self.engine.execute(sql)
        self.engine.dispose()
        DepotManager._clear()
        testing.tearDown()

    def test_downgrade_and_upgrade(self):
        """Test all migrations up and down.

        Tests that we can apply all migrations from a brand new empty
        database, and also that we can remove them all.
        """
        uri = self.app_config.SQLALCHEMY__URL
        folder = TEST_MIGRATION_SCRIPT_LOCATION

        alembic_config = Config()
        alembic_config.set_main_option("script_location", folder)
        alembic_config.set_main_option("sqlalchemy.url", uri)
        script = ScriptDirectory.from_config(alembic_config)

        # stamp last_revision
        head_revision = get_revision(alembic_config, self.engine, script, "head")
        current_revision = get_revision(alembic_config, self.engine, script, "current")
        assert current_revision is None
        head_revision = get_revision(alembic_config, self.engine, script, "head")
        command.stamp(alembic_config, head_revision)
        current_revision = get_revision(alembic_config, self.engine, script, "current")
        assert current_revision == head_revision

        # downgrade all revision
        while current_revision is not None:
            command.downgrade(alembic_config, "-1")
            current_revision = get_revision(alembic_config, self.engine, script, "current")
        assert current_revision is None
        # upgrade all revision
        while current_revision != head_revision:
            command.upgrade(alembic_config, "+1")
            current_revision = get_revision(alembic_config, self.engine, script, "current")

        assert current_revision == head_revision
