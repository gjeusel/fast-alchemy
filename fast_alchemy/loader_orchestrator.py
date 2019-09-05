"""
isort:skip_file
"""
import logging
from abc import ABCMeta, abstractmethod
from .helpers import ordered_load
from collections import namedtuple

from sqlalchemy.inspection import inspect as sqla_inspect

logger = logging.getLogger(__name__)

try:
    import openpyxl
    HAS_OPENPYXL = True
except ImportError:
    logger.debug('openpyxl is not installed. Excel loading is disabled.')
    HAS_OPENPYXL = False

ClassInfo = namedtuple('ClassInfo', 'class_name,inherits_class,inherits_name')


class BaseModelLoader(metaclass=ABCMeta):
    def __init__(self, base, class_registry):
        self.Model = base
        self.class_registry = class_registry

    @abstractmethod
    def load(self):
        pass

    @abstractmethod
    def parse_class_definition(self, class_definition):
        pass


def _parse_class_definition(base, class_registry, class_definition):
    inherits_class = (base, )
    class_name = class_definition
    inherits_name = None
    if '|' in class_definition:
        class_name, inherits_name = class_definition.split('|')
        inherits_class = (class_registry[inherits_name], )
    return ClassInfo(class_name, inherits_class, inherits_name)


class ModelLoader(BaseModelLoader):
    def parse_class_definition(self, class_definition):
        return _parse_class_definition(self.Model, self.class_registry, class_definition)

    def load(self, raw):
        for class_definition, fields in raw.items():
            class_info = self.parse_class_definition(class_definition)
            yield class_info, fields['definition']


class BaseInstanceLoader(metaclass=ABCMeta):
    def __init__(self, classes):
        self.classes = classes

    @abstractmethod
    def load(self, class_info, ref_name, instances, instance_refs):
        pass


class InstanceLoader(BaseInstanceLoader):
    def _scan_relations(self, klass):
        relations = []
        for rel in sqla_inspect(klass).relationships:
            if rel.direction.name == 'MANYTOONE':
                relations.append(rel.key)
        return relations

    def load(self, file_or_raw, class_info, ref_name, instances,
             instance_refs):
        klass = self.classes[class_info.class_name]
        for definition in instances:
            for relation in self._scan_relations(klass):
                clean_ref = self.clean_ref(definition[relation])
                related_instance = instance_refs[clean_ref]
                definition[relation] = related_instance
            instance = klass(**definition)
            instance_refs[self.build_ref(definition, ref_name)] = instance

    def build_ref(self, definition, ref_name):
        names = []
        for name in ref_name.split(','):
            name = name.strip()
            names.append(definition[name])
        return ','.join(names)

    def clean_ref(self, ref_name):
        names = []
        for name in ref_name.split(','):
            names.append(name.strip())
        return ','.join(names)


class LoaderOrchestrator:
    def __init__(self, model_loader, instance_loader):
        self.model_loader = model_loader
        self.instance_loader = instance_loader

    def _load_file(self, file_or_raw):
        raw = file_or_raw
        if isinstance(file_or_raw, str):

            # YAML
            if file_or_raw.lower().endswith(('.yml', '.yaml')):
                with open(file_or_raw, 'r') as fh:
                    raw = ordered_load(fh)

            # EXCEL
            elif file_or_raw.lower().endswith('.xlsx'):
                raise NotImplementedError

        return raw

    def models(self, filepath):
        raw = self._load_file(filepath)
        return self.model_loader.load(raw)

    def instances(self, filepath):
        instance_refs = {}
        for class_definition, fields in self._load_file(filepath):
            if not fields.get('instances'):
                continue
            class_info = self._parse_class_definition(class_definition)
            self.instance_loader.load(
                class_info, fields['ref'], fields['instances'], instance_refs)

        return instance_refs
