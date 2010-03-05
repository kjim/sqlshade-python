import unittest

class TagMeta(type):
    _classmap = {}

    def __init__(cls, clsname, bases, dict):
        print "TagMeta.__init__"
        if cls.__keyword__ is not None:
            cls._classmap[cls.__keyword__] = cls
            super(TagMeta, cls).__init__(clsname, bases, dict)

    def __call__(cls, keyword, text, **kwargs):
        print "TagMeta.__call__"
        try:
            cls = TagMeta._classmap[keyword]
        except KeyError:
            raise Exception()
        return type.__call__(cls, keyword, text, **kwargs)

class Tag(object):
    __metaclass__ = TagMeta
    __keyword__ = None

    def __init__(self, keyword, text, **kwargs):
        print "Tag.__init__"
        super(Tag, self).__init__(**kwargs)
        self.keyword = keyword
        self.text = text

class IncludeTag(Tag):
    __keyword__ = 'include'

    def __init__(self, keyword, text, **kwargs):
        print "IncludeTag.__init__"
        super(IncludeTag, self).__init__(keyword, text, **kwargs)

class InheritTag(Tag):
    __keyword__ = 'inherit'

    def __init__(self, keyword, text, **kwargs):
        print "InheritTag.__init__"
        super(InheritTag, self).__init__(keyword, text, **kwargs)

class MetaclassTringTest(unittest.TestCase):

    def test_metaclass_1(self):
        tag = Tag('include', 'argument text')
        assert type(tag) == IncludeTag
        assert tag.keyword == 'include'
        assert tag.text == 'argument text'

        tag = Tag('inherit', 'inherit argument')
        assert type(tag) == InheritTag
        assert tag.keyword == 'inherit'
        assert tag.text == 'inherit argument'
