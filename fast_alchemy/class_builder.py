from abc import ABCMeta, abstractmethod
from collections import defaultdict, namedtuple

import sqlalchemy as sa

FieldInfo = namedtuple('FieldInfo', 'field_name,field_definition,field_args')


class BaseClassBuilder(metaclass=ABCMeta):
    def __init__(self, db, field_builder):
        self.db = db
        self.backrefs = defaultdict(dict)
        self.field_builder = field_builder

    @abstractmethod
    def build(self, class_info, fields):
        pass


class ClassBuilder(BaseClassBuilder):
    def _parse_field(self, field_name, field_definition):
        field_args = []
        if '|' in field_definition:
            field_definition, args = field_definition.split('|')
            field_args = args.split(',')
        return FieldInfo(field_name, field_definition, field_args)

    def _parse_fields(self, fields, class_name):
        for field_name, field_definition in fields.items():
            field_info = self._parse_field(field_name, field_definition)
            if field_info.field_definition == 'Backref':
                self.backrefs[field_info.
                              field_args[0]][class_name] = field_name
            else:
                yield field_info

    def _prepare_polymorphic(self, field_def):
        mapper_args = {}
        for key, val in field_def.items():
            mapper_args['polymorphic_{}'.format(key)] = val
        return mapper_args

    def _build_pk(self, class_info):
        pk_args = [sa.Integer]
        if self.db.Model not in class_info.inherits_class:
            fk_id = '{}.id'.format(class_info.inherits_name.lower())
            pk_args.append(sa.ForeignKey(fk_id))
        return sa.Column(*pk_args, primary_key=True)

    def build(self, class_info, fields):
        class_name = class_info.class_name
        tablename = class_name.lower()

        class_attributes = {
            '__tablename__': tablename,
            'id': self._build_pk(class_info)
        }
        if class_info.inherits_name or 'polymorphic' in fields:
            polymorphic_def = fields.pop('polymorphic', {})
            polymorphic_def['identity'] = class_info.class_name.lower()
            definition = self._prepare_polymorphic(polymorphic_def)
            class_attributes['__mapper_args__'] = definition

        for field_info in self._parse_fields(fields, class_name):
            field = self.field_builder.build(field_info, class_name, self.backrefs)
            class_attributes.update(field)

        Klass = type(class_name, class_info.inherits_class, class_attributes)
        setattr(self.db, class_name, Klass)
        return Klass
