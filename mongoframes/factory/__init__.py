import copy
from blinker import signal

__all__ = ['Factory']


class Factory:
    """
    The `Factory` class is responsible for production of fake data for.
    Production of fake data is a two stage process:

    Assembly (see `assemble`)
    :   A `Quota` of documents is assembled based on a `Blueprint`.

        At this stage the documents contain a mixture of static and dynamic
        data. Dynamic data is data that will be transformed during population,
        for example a field might contain a value of `'now,tomorrow'` which on
        population will be converted to a date/time between now and tomorrow.

        Once assembled the generated documents are returned as a list and can be
        either used immediately to populate the database or saved out as a
        template for populating the database in future (for example when
            building a set of test data).

    Population (see `populate`)
    :   A database is populated based on a `Blueprint` and pre-assembled list of
        documents.

        During this stage dynamic data is converted to static data suitable for
        inserting in the database (this process is call finishing).

        Prior to and after inserting the a document into the database the
        `factory_insert` and `factory_inserted` events are triggered to allow
        `Frame` classes to modify the insert behaviour for factories.
    """

    def __init__(self, presets=None):
        # A list of presets for the factory
        self._presets = presets or []

    # Read-only properties

    @property
    def presets(self):
        return self._presets

    # Public methods

    def assemble(self, blueprint, quota):
        """Assemble a quota of fake documents"""

        # Reset the blueprint
        blueprint.reset()

        # Assemble the documents
        documents = []
        for i in range(0, int(quota)):
            documents.append(blueprint.assemble(self.presets))

        return documents

    def finish(self, blueprint, documents):
        """Apply finishing to a list of pre-assembled documents"""

        # Reset the blueprint
        blueprint.reset()

        # Finish the documents
        finished = []
        for document in documents:
            finished.append(blueprint.finish(document, self.presets))

        return finished

    def populate(self, blueprint, documents):
        """Populate the database with fake documents"""

        # Finish the documents
        documents = self.finish(blueprint, documents)

        # Convert the documents to frame instances
        frames = blueprint.frame_cls._ensure_frames(documents)

        # Insert the documents (only if the frame class
        signal('factory_insert').send(blueprint.frame_cls, frames=frames)
        frames = blueprint.frame_cls.insert_many(frames)
        signal('factory_inserted').send(blueprint.frame_cls, frames=frames)

    #def seed
    #
    # random, faker