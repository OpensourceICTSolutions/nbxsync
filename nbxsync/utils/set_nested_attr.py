def set_nested_attr(obj, attr_path, value):
    """
    Set a nested attribute on an object using a dotted path.
    E.g., set_nested_attr(obj, "foo.bar.baz", 123) sets obj.foo.bar.baz = 123
    """
    attrs = attr_path.split('.')
    for attr in attrs[:-1]:
        obj = getattr(obj, attr)
        if obj is None:
            raise AttributeError(f"Cannot set '{attr_path}': '{attr}' is None in the path.")
    setattr(obj, attrs[-1], value)
