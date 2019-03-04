import os

from flask import Flask
from flask_sqlalchemy import SQLAlchemy

from fast_alchemy import FastAlchemy

ROOT_DIR = os.path.dirname(__file__)
DATA_DIR = os.path.join(ROOT_DIR, 'data')


def test_it_can_load_instances():
    app = Flask(__name__)
    db = SQLAlchemy(app)
    fa = FastAlchemy(db)
    fa.load(os.path.join(DATA_DIR, 'instances.yaml'))
    assert len(db.AntCollection.query.all()) == 3
    assert len(db.SandwichFormicarium.query.all()) == 3
    assert len(db.FreeStandingFormicarium.query.all()) == 2
    assert len(db.AntColony.query.all()) == 6
