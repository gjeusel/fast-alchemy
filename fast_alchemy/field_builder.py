from abc import ABCMeta, abstractmethod

import sqlalchemy as sa

FIELD_LOCATIONS = [sa, sa.orm]
NO_COLUMN_FOR = ['relationship']


class BaseFieldBuilder(metaclass=ABCMeta):
    @abstractmethod
    def build(self, field_info, class_name, backrefs):
        pass


class FieldBuilder(BaseFieldBuilder):
    def build(self, field_info, class_name, backrefs):
        fields = {}
        kwargs = {}

        if field_info.field_definition == 'relationship':
            fk_name, fk = self._build_relation(field_info)
            fields[fk_name] = fk
            kwargs['backref'] = backrefs[class_name][field_info.field_args[0]]

        field_type = None
        for location in FIELD_LOCATIONS:
            if hasattr(location, field_info.field_definition):
                field_type = getattr(location, field_info.field_definition)
        if not field_type:
            raise Exception('{} could not be found'.format(field_type))

        field = field_type(*field_info.field_args, **kwargs)
        if field_info.field_definition not in NO_COLUMN_FOR:
            field = sa.Column(field_info.field_name, field)
        fields[field_info.field_name] = field
        return fields

    def _build_relation(self, field_info):
        fk_name = '{}_id'.format(field_info.field_name)
        fk_relation = '{}.id'.format(field_info.field_args[0].lower())
        fk = sa.Column(fk_name, sa.Integer, sa.ForeignKey(fk_relation))
        return fk_name, fk
