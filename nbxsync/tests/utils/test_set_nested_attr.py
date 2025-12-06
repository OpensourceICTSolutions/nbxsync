from django.test import TestCase

from nbxsync.utils.set_nested_attr import set_nested_attr


class DummyInner:
    def __init__(self):
        self.baz = None


class DummyMiddle:
    def __init__(self):
        self.bar = DummyInner()


class DummyRoot:
    def __init__(self):
        self.foo = DummyMiddle()


class SetNestedAttrTestCase(TestCase):
    def setUp(self):
        self.root = DummyRoot()

    def test_set_simple_attribute(self):
        set_nested_attr(self.root, 'foo', DummyMiddle())
        self.assertIsInstance(self.root.foo, DummyMiddle)

    def test_set_nested_attribute_success(self):
        # Set deeply nested attribute foo.bar.baz
        set_nested_attr(self.root, 'foo.bar.baz', 123)
        self.assertEqual(self.root.foo.bar.baz, 123)

    def test_raises_attribute_error_when_intermediate_is_none(self):
        # Break the chain
        self.root.foo.bar = None
        with self.assertRaises(AttributeError) as cm:
            set_nested_attr(self.root, 'foo.bar.baz', 999)
        self.assertIn("'bar' is None", str(cm.exception))
        self.assertIn('foo.bar.baz', str(cm.exception))

    def test_creates_expected_value_type(self):
        # Assign a string value
        set_nested_attr(self.root, 'foo.bar.baz', 'test-value')
        self.assertEqual(self.root.foo.bar.baz, 'test-value')
        self.assertIsInstance(self.root.foo.bar.baz, str)

    def test_single_level_attribute_path(self):
        # Single attribute path (no dot)
        dummy = DummyInner()
        set_nested_attr(dummy, 'baz', 42)
        self.assertEqual(dummy.baz, 42)

    def test_invalid_path_raises_attributeerror(self):
        # Attribute missing entirely
        with self.assertRaises(AttributeError):
            set_nested_attr(self.root, 'nonexistent.attr', 123)
