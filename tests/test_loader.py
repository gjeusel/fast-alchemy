import pytest

from fast_alchemy import FastAlchemy
from fast_alchemy.loader import YAMLInstanceLoader


@pytest.fixture
def fa(ModelBase, session):
    return FastAlchemy(ModelBase, session)


class TestLoaderSelection:
    @pytest.mark.parametrize((
        'filepath, expected',
        ('some.yml', YAMLInstanceLoader),
    ))
    def test_select_yaml_loader_default(self, fa, filepath):
        pass
