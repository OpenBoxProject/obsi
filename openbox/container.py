"""
Various containers.
"""


def recursion_lock(retval, lock_name="__recursion_lock__"):
    def decorator(func):
        def wrapper(self, *args, **kw):
            if getattr(self, lock_name, False):
                return retval
            setattr(self, lock_name, True)
            try:
                return func(self, *args, **kw)
            finally:
                setattr(self, lock_name, False)

        wrapper.__name__ = func.__name__
        return wrapper

    return decorator


class Container(dict):
    """
    A generic container of attributes.

    Containers are the common way to express parsed data.
    """
    __slots__ = ["__keys_order__"]

    def __init__(self, **kw):
        object.__setattr__(self, "__keys_order__", [])
        for k, v in kw.items():
            self[k] = v

    def __getattr__(self, name):
        try:
            return self[name]
        except KeyError:
            raise AttributeError(name)

    def __setitem__(self, key, val):
        if key not in self:
            self.__keys_order__.append(key)
        dict.__setitem__(self, key, val)

    def __delitem__(self, key):
        dict.__delitem__(self, key)
        self.__keys_order__.remove(key)

    __delattr__ = __delitem__
    __setattr__ = __setitem__

    def clear(self):
        dict.clear(self)
        del self.__keys_order__[:]

    def pop(self, key, *default):
        val = dict.pop(self, key, *default)
        self.__keys_order__.remove(key)
        return val

    def popitem(self):
        k, v = dict.popitem(self)
        self.__keys_order__.remove(k)
        return k, v

    def update(self, seq, **kw):
        if hasattr(seq, "keys"):
            for k in seq.keys():
                self[k] = seq[k]
        else:
            for k, v in seq:
                self[k] = v
        dict.update(self, kw)

    def copy(self):
        inst = self.__class__()
        inst.update(self.iteritems())
        return inst

    __update__ = update
    __copy__ = copy

    def __iter__(self):
        return iter(self.__keys_order__)

    iterkeys = __iter__

    def itervalues(self):
        return (self[k] for k in self.__keys_order__)

    def iteritems(self):
        return ((k, self[k]) for k in self.__keys_order__)

    def keys(self):
        return self.__keys_order__

    def values(self):
        return list(self.itervalues())

    def items(self):
        return list(self.iteritems())

    def __repr__(self):
        return "%s(%s)" % (self.__class__.__name__, dict.__repr__(self))

    @recursion_lock("<...>")
    def __pretty_str__(self, nesting=1, indentation="    "):
        attrs = []
        ind = indentation * nesting
        for k, v in self.iteritems():
            if not k.startswith("_"):
                text = [ind, k, " = "]
                if hasattr(v, "__pretty_str__"):
                    text.append(v.__pretty_str__(nesting + 1, indentation))
                else:
                    text.append(repr(v))
                attrs.append("".join(text))
        if not attrs:
            return "%s()" % (self.__class__.__name__,)
        attrs.insert(0, self.__class__.__name__ + ":")
        return "\n".join(attrs)

    __str__ = __pretty_str__
