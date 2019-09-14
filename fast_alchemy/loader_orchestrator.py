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
    def parse_class_definition(self, class_definition):
        pass

    @abstractmethod
    def load_yml(self):
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
        return _parse_class_definition(self.Model, self.class_registry,
                                       class_definition)

    def load_yml(self, raw):
        for class_definition, fields in raw.items():
            class_info = self.parse_class_definition(class_definition)
            yield class_info, fields['definition']


class BaseInstanceLoader(metaclass=ABCMeta):
    def __init__(self, classes):
        self.classes = classes

    @abstractmethod
    def load_yml(self, class_info, ref_name, instances, instance_refs):
        pass

    @abstractmethod
    def load_xlsx(self, class_info, ref_name, instances, instance_refs):
        pass


class InstanceLoader(BaseInstanceLoader):
    def _scan_relations(self, klass):
        relations = []
        for rel in sqla_inspect(klass).relationships:
            if rel.direction.name == 'MANYTOONE':
                relations.append(rel.key)
        return relations

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

    def _one_definition_load_yml(self, class_info, ref_name, instances,
                                 instance_refs):
        klass = self.classes[class_info.class_name]
        for definition in instances:
            for relation in self._scan_relations(klass):
                clean_ref = self.clean_ref(definition[relation])
                related_instance = instance_refs[clean_ref]
                definition[relation] = related_instance
            instance = klass(**definition)
            instance_refs[self.build_ref(definition, ref_name)] = instance

    def load_yml(self, class_info, raw):
        instance_refs = {}
        for class_definition, fields in raw:
            if not fields.get('instances'):
                continue
            self._one_definition_load_yml(class_info, fields['ref'],
                                          fields['instances'], instance_refs)

        return instance_refs

    def load_xlsx(self, class_info, raw):
        raise NotImplementedError


METHOD_MAPPING = {
    'yml': 'load_yml',
    'xlsx': 'load_xlsx',
}


class LoaderOrchestrator:
    def __init__(self, model_loader, instance_loader):
        self.model_loader = model_loader
        self.instance_loader = instance_loader

    def _load_file(self, file_or_raw, ft=None):
        raw = file_or_raw
        if isinstance(file_or_raw, str):

            # YAML
            if file_or_raw.lower().endswith(('.yml', '.yaml')):
                with open(file_or_raw, 'r') as fh:
                    raw = ordered_load(fh)
                    method = METHOD_MAPPING['yml']

            # EXCEL
            elif file_or_raw.lower().endswith('.xlsx'):
                if not HAS_OPENPYXL:
                    msg = 'For Excel files, you need to install openpyxl.'
                    raise ImportError(msg)
                raise NotImplementedError

        else:
            if ft is None:
                msg = "Can't deduce filetype from io {}"
                raise Exception(msg.format(msg))
            if ft.lower() not in METHOD_MAPPING:
                msg = "Unknown filetype '{}'".format(ft)
                raise Exception(msg)
            method = METHOD_MAPPING[ft.lower()]

        return raw, method

    def models(self, filepath, ft=None):
        raw, method = self._load_file(filepath, ft)
        fn = getattr(self.model_loader, method)
        return fn(raw)

    def instances(self, filepath, ft=None):
        raw, method = self._load_file(filepath, ft)
        fn = getattr(self.instance_loader, method)
        return fn(self.model_loader.class_registry, raw)
