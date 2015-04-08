import unittest
from random import randint
from openbox.container import Container


class TestContainer(unittest.TestCase):

    def test_getattr(self):
        c = Container(a=1)
        self.assertEqual(c["a"], c.a)

    def test_setattr(self):
        c = Container()
        c.a = 1
        self.assertEqual(c["a"], 1)

    def test_delattr(self):
        c = Container(a=1)
        del c.a
        self.assertFalse("a" in c)

    def test_update(self):
        c = Container(a=1)
        d = Container()
        d.update(c)
        self.assertEqual(d.a, 1)

    def test_eq_eq(self):
        c = Container(a=1)
        d = Container(a=1)
        self.assertEqual(c, d)

    def test_ne_wrong_type(self):
        c = Container(a=1)
        d = [("a", 1)]
        self.assertNotEqual(c, d)

    def test_ne_wrong_key(self):
        c = Container(a=1)
        d = Container(b=1)
        self.assertNotEqual(c, d)

    def test_ne_wrong_value(self):
        c = Container(a=1)
        d = Container(a=2)
        self.assertNotEqual(c, d)

    def test_copy(self):
        c = Container(a=1)
        d = c.copy()
        self.assertEqual(c, d)
        self.assertTrue(c is not d)

    def test_copy_module(self):
        from copy import copy

        c = Container(a=1)
        d = copy(c)
        self.assertEqual(c, d)
        self.assertTrue(c is not d)

    def test_bool_false(self):
        c = Container()
        self.assertFalse(c)

    def test_bool_true(self):
        c = Container(a=1)
        self.assertTrue(c)

    def test_in(self):
        c = Container(a=1)
        self.assertTrue("a" in c)

    def test_not_in(self):
        c = Container()
        self.assertTrue("a" not in c)

    def test_repr(self):
        c = Container(a=1, b=2)
        repr(c)

    def test_repr_recursive(self):
        c = Container(a=1, b=2)
        c.c = c
        repr(c)

    def test_str(self):
        c = Container(a=1, b=2)
        str(c)

    def test_str_recursive(self):
        c = Container(a=1, b=2)
        c.c = c
        str(c)
    
    def test_order(self):
        c = Container()
        words = None  # just to keep intellij happy
        while True:
            words = [("".join(chr(randint(65, 97)) for _ in range(randint(3, 7))), i) for i in range(20)]
            if words != list(dict(words).keys()):
                break
        c.update(words)
        self.assertEqual([k for k, _ in words], list(c.keys()))

    def test_get_path(self):
        c = Container(a=Container(b=Container(d=1, e=2), c=1))
        res = c.get_path('a.b.d')
        self.assertEqual(res, 1)

    def test_default_get_path(self):
        c = Container(a=Container(b=Container(d=1, e=2), c=1))
        res = c.get_path('a.b.non', "nop")
        self.assertEqual(res, 'nop')

    def test_set_path(self):
        c = Container(a=Container(b=Container(d=1, e=2), c=1))
        expected = Container(a=Container(b=Container(d=1, e=2, new_value=5), c=1))
        c.set_path('a.b.new_value', 5)
        self.assertEqual(expected, c)

    def test_set_path_at_root(self):
        c = Container(a=Container(b=Container(d=1, e=2), c=1))
        expected = Container(new_value=6, a=Container(b=Container(d=1, e=2), c=1))
        c.set_path('new_value', 6)
        self.assertEqual(expected, c)
