import re

from mongoframes.factory import blueprints
from mongoframes.factory import makers
from mongoframes.factory import quotas
from mongoframes.factory.makers import selections as selection_makers
from mongoframes.factory.makers import text as text_makers

from tests.fixtures import *


def test_maker():
    """
    The base maker class should provide context for the current target document.
    """

    document = {'foo': 'bar'}
    maker = makers.Maker()

    # Check the target for the maker is correctly set using the `target` context
    # method.
    with maker.target(document):
        assert maker.document == document

    # Once the maker falls out of context check the document has been unset
    assert maker.document == None

def test_dict_of():
    """
    `DictOf` makers should return a dictionary where each key's value is either
    a JSON type value the output of a maker.
    """

    maker = makers.DictOf({
        'json_type': 'foo',
        'maker': makers.Lambda(lambda doc: 'bar')
        })

    # Check the assembled result
    assembled = maker._assemble()
    assert assembled == {
        'json_type': None,
        'maker': 'bar'
    }

    # Check the finished result
    finished = maker._finish(assembled)
    assert finished == {
        'json_type': 'foo',
        'maker': 'bar'
    }

def test_faker():
    """
    `Faker` makers should call a faker library provider and return the output as
    the value.
    """
    am_pm = {'AM', 'PM'}

    # Configured as assembler
    maker = makers.Faker('am_pm')

    # Check the assembled result
    assembled = maker._assemble()
    assert assembled in am_pm

    # Check the finished result
    finished = maker._finish(assembled)
    assert finished in am_pm

    # Configured as finisher
    maker = makers.Faker('am_pm', assembler=False)

    # Check the assembled result
    assembled = maker._assemble()
    assert assembled == None

    # Check the finished result
    finished = maker._finish(assembled)
    assert finished in am_pm

    # Configured with a different locale
    maker = makers.Faker('postcode', locale='en_GB')

    # Check the assembled result resembles a UK postcode
    assembled = maker._assemble()

    assert re.match('(\w+?\d{1,2}).*', assembled) and len(assembled) <= 8

def test_lambda():
    """
    `Lambda` makers should return the output of the function you initialize them
    with.
    """

    # Configured as assembler
    maker = makers.Lambda(lambda doc: 'foo')

    # Check the assembled result
    assembled = maker._assemble()
    assert assembled == 'foo'

    # Check the finished result
    finished = maker._finish(assembled)
    assert finished == 'foo'

    # Configured as finisher
    maker = makers.Lambda(lambda doc, v: 'bar', assembler=False, finisher=True)

    # Check the assembled result
    assembled = maker._assemble()
    assert assembled == None

    # Check the finished result
    finished = maker._finish(assembled)
    assert finished == 'bar'

    # Configured as both an assembler and finisher
    def func(doc, value=None):
        if value:
            return value + 'bar'
        return 'foo'

    maker = makers.Lambda(func, finisher=True)

    # Check the assembled result
    assembled = maker._assemble()
    assert assembled == 'foo'

    # Check the finished result
    finished = maker._finish(assembled)
    assert finished == 'foobar'

def test_list_of():
    """
    `ListOf` makers should return a list of values generated by calling a maker
    multiple times.
    """

    # Configured to not reset sub-maker
    maker = makers.ListOf(
        selection_makers.Cycle(list('abcde')),
        quotas.Quota(6)
        )

    # Check the assembled result
    assembled = maker._assemble()
    assert assembled == [[i, None] for i in [0, 1, 2, 3, 4, 0]]

    # Check the finished result
    finished = maker._finish(assembled)
    assert finished == list('abcdea')

    # Check that calling the maker again continues from where we left off
    assembled = maker._assemble()
    assert assembled == [[i, None] for i in [1, 2, 3, 4, 0, 1]]

    # Configured to reset sub-maker
    maker = makers.ListOf(
        selection_makers.Cycle(list('abcde')),
        quotas.Quota(6),
        reset_maker=True
        )

    # Call the maker twice
    assembled = maker._assemble()
    assembled = maker._assemble()

    # Check the result was reset after the first call
    assert assembled == [[i, None] for i in [0, 1, 2, 3, 4, 0]]

def test_reference(mongo_client, example_dataset_one):
    """
    `Reference` makers should return the `_id` value for a document in a
    collection looked up using the field name and value.
    """

    # Configured with static value
    maker = makers.Reference(ComplexDragon, 'name', 'Burt')

    # Check the assembled result
    assembled = maker._assemble()
    assert assembled == None

    # Check the finished result
    finished = maker._finish(assembled)
    assert finished == ComplexDragon.one()._id

    # Configured with maker
    maker = makers.Reference(ComplexDragon, 'name', makers.Static('Burt'))

    # Check the assembled result
    assembled = maker._assemble()
    assert assembled == 'Burt'

    # Check the finished result
    finished = maker._finish(assembled)
    assert finished == ComplexDragon.one()._id

def test_static():
    """`Static` makers should return the value you initialize them with"""

    # Configured as assembler
    value = {'foo': 'bar'}
    maker = makers.Static(value)

    # Check the assembled result
    assembled = maker._assemble()
    assert assembled == value

    # Check the finished result
    finished = maker._finish(assembled)
    assert finished == value

    # Configured as finisher
    value = {'foo': 'bar'}
    maker = makers.Static(value, assembler=False)

    # Check the assembled result
    assembled = maker._assemble()
    assert assembled == None

    # Check the finished result
    finished = maker._finish(assembled)
    assert finished == value

def test_sub_factory(mocker):
    """
    `SubFactory` makers should return a sub-frame/document using a blueprint.
    """

    # Define a blueprint
    class InventoryBlueprint(blueprints.Blueprint):

        _frame_cls = Inventory

        gold = makers.Static(10)
        skulls = makers.Static(100)

    # Configure the maker
    maker = makers.SubFactory(InventoryBlueprint)

    # Check the assembled result
    assembled = maker._assemble()
    assert assembled == {'gold': 10, 'skulls': 100}

    # Check the finished result
    finished = maker._finish(assembled)
    assert isinstance(finished, Inventory)
    assert finished._document == {'gold': 10, 'skulls': 100}

    # Reset should reset the sub factories associated blueprint
    mocker.spy(InventoryBlueprint, 'reset')
    maker.reset()
    assert InventoryBlueprint.reset.call_count == 1

def test_unique():
    """
    `Unique` makers guarentee a unique value is return from the maker they are
    wrapped around.
    """

    # Confifured as assembler
    maker = makers.Unique(makers.Faker('name'))

    # Generate 100 random names
    names = set([])
    for i in range(0, 20):
        assembled = maker._assemble()
        assert assembled not in names
        names.add(assembled)

    # Confifured as finisher
    maker = makers.Unique(makers.Faker('name'), assembler=False)

    # Generate 100 random names
    names = set([])
    for i in range(0, 20):
        finished = maker._finish(maker._assemble())
        assert finished not in names
        names.add(finished)

    # Check that unique will eventually fail if it cannot generate a unique
    # response with a maker.
    maker = makers.Unique(makers.Static('foo'))

    failed = False
    try:
        for i in range(0, 100):
            finished = maker._finish(maker._assemble())
    except AssertionError:
        failed = True

    assert failed

    # Check that we can include a set of initial exluded values
    maker = makers.Unique(
        text_makers.Sequence('test-{index}'),
        exclude={'test-3'}
        )

    names = set([])
    for i in range(0, 9):
        assembled = maker._assemble()
        names.add(assembled)

    assert 'test-3' not in names

    # Reset should clear the generate unique values from the maker and allow
    # those values to be generated again.
    maker = makers.Unique(makers.Static('foo'))

    failed = False
    try:
        for i in range(0, 100):
            finished = maker._finish(maker._assemble())
            maker.reset()

    except AssertionError:
        failed = True

    assert not failed