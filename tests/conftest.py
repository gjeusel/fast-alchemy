import os
import tempfile

import pytest
import sqlalchemy as sa


@pytest.yield_fixture(scope='function')
def temp_file(request):
    fd, path = tempfile.mkstemp(suffix='.py')
    yield path
    os.close(fd)
    os.remove(path)


@pytest.fixture(scope='function')
def engine():
    return sa.create_engine('sqlite:///:memory:')


@pytest.fixture(scope='function')
def ModelBase(engine):
    Base = sa.ext.declarative.declarative_base()
    Base.metadata.bind = engine
    return Base


@pytest.fixture(scope='function')
def session(engine):
    Session = sa.orm.sessionmaker(
        autocommit=False, autoflush=False, bind=engine)
    return sa.orm.scoped_session(Session)
