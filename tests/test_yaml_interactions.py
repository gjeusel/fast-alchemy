import importlib
import os

from flask import Flask
from flask_sqlalchemy import SQLAlchemy

from fast_alchemy import FastAlchemy, FlaskFastAlchemy
from fast_alchemy.export import FastAlchemyExporter

ROOT_DIR = os.path.dirname(__file__)
DATA_DIR = os.path.join(ROOT_DIR, 'data')


def test_it_can_load_instances(ModelBase, session):
    fa = FastAlchemy(ModelBase, session)
    with fa:
        fa.load(os.path.join(DATA_DIR, 'instances.yaml'))
    fa.load(os.path.join(DATA_DIR, 'instances.yaml'))
    assert len(session.query(fa.AntCollection).all()) == 4
    assert len(session.query(fa.SandwichFormicarium).all()) == 3
    assert len(session.query(fa.FreeStandingFormicarium).all()) == 2
    assert len(session.query(fa.AntColony).all()) == 6


def test_it_can_load_from_flask_sqlalchemy():
    app = Flask(__name__)
    app.config['SQLALCHEMY_DATABASE_URI'] = "sqlite:///:memory:"
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    db = SQLAlchemy(app)

    fa = FlaskFastAlchemy(db)
    with fa:
        fa.load(os.path.join(DATA_DIR, 'instances.yaml'))
    fa.load(os.path.join(DATA_DIR, 'instances.yaml'))
    assert len(fa.AntCollection.query.all()) == 4
    assert len(fa.SandwichFormicarium.query.all()) == 3
    assert len(fa.FreeStandingFormicarium.query.all()) == 2
    assert len(fa.AntColony.query.all()) == 6


def test_it_can_export_models_to_python_code(temp_file):
    fa = FastAlchemyExporter()
    with open(os.path.join(DATA_DIR, temp_file), 'w') as fh:
        fa.export_to_python(os.path.join(DATA_DIR, 'instances.yaml'), fh)

    spec = importlib.util.spec_from_file_location('models', temp_file)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    fa = FastAlchemy(module.Base, module.session)
    fa.load_instances(os.path.join(DATA_DIR, 'instances.yaml'))
    session = module.session
    assert len(session.query(module.AntCollection).all()) == 4
    assert len(session.query(module.SandwichFormicarium).all()) == 3
    assert len(session.query(module.FreeStandingFormicarium).all()) == 2
    assert len(session.query(module.AntColony).all()) == 6
