import unittest

class PhantomTagMeta(type):
    _classmap = {}

    def __init__(cls, clsname, bases, dict):
        print "PhantomTagMeta.__init__"
        if cls.__keyword__ is not None:
            cls._classmap[cls.__keyword__] = cls
            super(PhantomTagMeta, cls).__init__(clsname, bases, dict)

    def __call__(cls, keyword, text, **kwargs):
        print "PhantomTagMeta.__call__"
        try:
            cls = PhantomTagMeta._classmap[keyword]
        except KeyError:
            raise Exception()
        return type.__call__(cls, keyword, text, **kwargs)

class PhantomTag(object):
    __metaclass__ = PhantomTagMeta
    __keyword__ = None

    def __init__(self, keyword, text, **kwargs):
        print "Tag.__init__"
        super(PhantomTag, self).__init__(**kwargs)
        self.keyword = keyword
        self.text = text

class ForTag(PhantomTag):
    __keyword__ = 'for'

    def __init__(self, keyword, text, **kwargs):
        print "ForTag.__init__"
        super(ForTag, self).__init__(keyword, text, **kwargs)

class IfTag(PhantomTag):
    __keyword__ = 'if'

    def __init__(self, keyword, text, **kwargs):
        print "IfTag.__init__"
        super(IfTag, self).__init__(keyword, text, **kwargs)

class MetaclassTringTest(unittest.TestCase):

    def test_metaclass_1(self):
        tag = PhantomTag('for', 'item in :iter_items')
        assert type(tag) == ForTag
        assert tag.keyword == 'for'
        assert tag.text == 'item in :iter_items'

        tag = PhantomTag('if', ':boolean_item')
        assert type(tag) == IfTag
        assert tag.keyword == 'if'
        assert tag.text == ':boolean_item'
