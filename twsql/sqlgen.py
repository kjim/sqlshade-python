from twsql import exc, util

def compile(node, filename, data,
            source_encoding=None,
            generate_unicode=True):
    buf = util.FastEncodingBuffer()
    printer = QueryPrinter(buf)
    CompileSQL(printer, CompileContext(data), node)
    return printer.freeze()

class CompileContext(object):

    def __init__(self, data, **env):
        self._data = data
        self._env = env

    @property
    def data(self):
        return self._data

    @property
    def env(self):
        return self._env

class QueryPrinter(object):

    def __init__(self, buf):
        self._sql_fragments = buf
        self._bound_variables = []
        self.compiled_sql = None

    def write(self, fragment):
        self._sql_fragments.write(fragment)

    def bind(self, variable):
        self._bound_variables.append(variable)

    def freeze(self):
        return self._sql_fragments.getvalue(), self._bound_variables


SUPPORTED_BINDING_DATA_TYPES = (str, unicode, int, long, list, tuple)
ITERABLE_DATA_TYPES = (list, tuple)
NOT_ITERABLE_DATA_TYPES = tuple([datatype
                                 for datatype in SUPPORTED_BINDING_DATA_TYPES
                                 if datatype not in ITERABLE_DATA_TYPES])

def _resolve_value_in_context_data(ident, data):
    ident_struct = ident.split('.')
    if '' in ident_struct:
        raise KeyError(ident)
    tmp = data
    for e in ident_struct:
        tmp = tmp[e]
    return tmp

class CompileSQL(object):

    def __init__(self, printer, context, node):
        self.printer = printer
        self.node = node

        # begin compilation
        for n in self.node.get_children():
            n.accept_visitor(self, context)

    def visitLiteral(self, node, context):
        self.printer.write(node.text)

    def visitSubstituteComment(self, node, context):
        data = context.data
        try:
            variable = _resolve_value_in_context_data(node.ident, data)
            variable_type = type(variable)
        except KeyError, e:
            raise exc.RuntimeError("Couldn't resolve binding data: '%s'" % node.ident)
        else:
            if variable_type not in SUPPORTED_BINDING_DATA_TYPES:
                raise exc.RuntimeError("Binding data is invalid type: (%s, %r)" % (node.ident, type(variable)))
        if variable_type in ITERABLE_DATA_TYPES:
            self.printer.write('(' + ', '.join(['?' for v in variable]) + ')')
            for v in variable:
                self.printer.bind(v)
        else:
            self.printer.write('?')
            self.printer.bind(variable)

    def visitEmbed(self, node, context):
        if node.ident not in context.data:
            raise exc.RuntimeError("Has no '%s' variable." % node.ident)
        self.printer.write(context.data[node.ident])

    def visitIf(self, node, context):
        if node.ident not in context.data:
            raise exc.RuntimeError("Has no '%s' variable." % node.ident)
        if context.data[node.ident]:
            for n in node.get_children():
                n.accept_visitor(self, context)

    def visitFor(self, node, context):
        if node.ident not in context.data:
            raise exc.RuntimeError("Has no '%s' variable." % node.ident)
        alias = node.item
        for iterdata in context.data[node.ident]:
            for_block_context = CompileContext({alias: iterdata})
            for n in node.get_children():
                n.accept_visitor(self, for_block_context)
