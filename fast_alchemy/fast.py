from .class_builder import ClassBuilder
from .field_builder import FieldBuilder
from .helpers import scan_current_models
from .loader_orchestrator import InstanceLoader, LoaderOrchestrator, ModelLoader

MAPPING_REGISTRY = {
    'FastAlchemy': 'fast_alchemy',
    'FlaskFastAlchemy': 'flask_sqlalchemy',
}


class Options:
    def __init__(self, **kwargs):
        self.class_builder = kwargs.pop('class_builder', ClassBuilder)
        self.field_builder = kwargs.pop('field_builder', FieldBuilder)
        self.model_loader = kwargs.pop('model_loader', ModelLoader)
        self.instance_loader = kwargs.pop('instance_loader', InstanceLoader)


class FastAlchemy:
    """
    Convert yaml/excel into ORM datamodel on the fly.

    Args:
        base (DeclarativeMeta): a base class for declarative class definitions.
        session (scoped_session): user defined session scope to manage operations
            for ORM-mapped objects.
        kwargs: pattern injection for ClassBuilder, FieldBuilder and InstanceLoader.

    """

    def __init__(self, base, session, **kwargs):
        self.Model = base
        self.session = session
        self.options = Options(**kwargs)

        self.class_registry = {}
        self._context_registry = {}
        self.in_context = False

    def __enter__(self):
        self.in_context = True
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.drop_models(models=self._context_registry.keys())
        self._context_registry = {}
        self.in_context = False

    @property
    def field_builder(self):
        if not hasattr(self, '_field_builder'):
            self._field_builder = self.options.field_builder()
        return self._field_builder

    @property
    def class_builder(self):
        if not hasattr(self, '_class_builder'):
            self._class_builder = self.options.class_builder(
                self, self.field_builder)
        return self._class_builder

    @property
    def loader(self):
        # Update class_registry by inspecting the existant
        classes = scan_current_models(self)
        self.class_registry.update(classes)

        model_loader = self.options.model_loader(
            base=self.Model, class_registry=self.class_registry)
        instance_loader = self.options.instance_loader(classes=classes)

        return LoaderOrchestrator(model_loader, instance_loader)

    def load(self, filepath):
        self.load_models(filepath)
        self.load_instances(filepath)

    def load_models(self, filepath):
        registry = {}

        for class_info, definition in self.loader.models(filepath):
            klass = self.class_builder.build(class_info, definition)
            registry[class_info.class_name] = klass

        # Add subset registry to attribute class_registry
        self.class_registry.update(registry)

        # if in context, keep track of it
        if self.in_context:
            self._context_registry.update(registry)

        # End up by creating the actual sql tables in the database on the
        # registry subset
        self.create_tables(registry.keys())

    def load_instances(self, filepath):
        instance_refs = self.loader.load_instances(filepath)

        # Persist definitions
        self.session.add_all(instance_refs.values())
        self.session.commit()

    def _execute_for(self, tables, operation):
        op = getattr(self.Model.metadata, operation)
        op(bind=self.session.bind, tables=tables)

    def get_tables(self, models=None):
        """Get the tables of the registry. Can be applied on a subset of the model.
        Appliying it on a subset is used for example in the context exiting.

        Args:
            models (iterable): keys of the registry for which we want to get the tables.
                Default is None, meaning every keys.
        """
        if models is None:
            models = self.class_registry.keys()
        return [
            v.__table__ for (k, v) in self.class_registry.items()
            if k in models
        ]

    def drop_models(self, models=None):
        """Cleanup any Metadata, Registry and Attributes link to this models.
        Can be applied on a subset of models.

        Args:
            models (iterable): keys of the registry for which we want to get the table.
                Default is None, meaning every keys.
        """
        tables = self.get_tables(models)
        self._execute_for(tables, 'drop_all')

        for class_name in models or self.class_registry.keys():
            # registry cleaning
            reg = self.Model._decl_class_registry['_sa_module_registry']
            reg_name = MAPPING_REGISTRY[self.__class__.__name__]
            reg.contents[reg_name]._remove_item(class_name)
            self.Model._decl_class_registry.pop(class_name)

            # remove obj from metadata
            self.Model.metadata.remove(
                self.Model.metadata.tables[class_name.lower()])

            # Remove this class from self attributes
            # (which have been set by the ClassBuilder)
            delattr(self, class_name)

        # Reset class_registry dict
        # Will be re-loaded for the pre-existant if load_models
        self.class_registry = {}

    def create_tables(self, models=None):
        """Create all the tables of the models. Can also be applied on a subset of the model.

        Args:
            models (iterable): keys of the registry for which we want to create the tables.
        """
        tables = self.get_tables(models)
        self.execute_for(tables, 'create_all')


class FlaskFastAlchemy(FastAlchemy):
    def __init__(self, db):
        super().__init__(db.Model, db.session)
