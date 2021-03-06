from sqlshade import exc, util, tree
from sqlshade.lexer import Lexer

def compile(node, filename, data,
            source_encoding=None,
            generate_unicode=True,
            strict=True,
            parameter_format='list'):
    render_context = RenderContext(data, strict=strict)
    if parameter_format in RENDER_FACTORY:
        return RENDER_FACTORY[parameter_format](node, render_context)
    else:
        raise exc.ArgumentError("Unsupported parameter format: %s" % parameter_format)

def render_as_list_params(node, context):
    printer = ListStatementPrinter(util.FastEncodingBuffer())
    RenderListStatement(printer, context, node)
    return printer.freeze()

def render_as_dict_params(node, context):
    printer = DictStatementPrinter(util.FastEncodingBuffer())
    RenderDictStatement(printer, context, node)
    return printer.freeze()

RENDER_FACTORY = {
    'list': render_as_list_params,
    'dict': render_as_dict_params,

    list: render_as_list_params,
    dict: render_as_dict_params,
}

class RenderContext(object):

    def __init__(self, data, **env):
        self._data = data
        self._env = env

        self._mode = 'strict' if env['strict'] else 'nostrict'

    def update(self, **kwargs):
        self._data.update(**kwargs)

    @property
    def data(self):
        return self._data

    @property
    def env(self):
        return self._env

    @property
    def mode(self):
        return self._mode

class QueryStatementPrinter(object):

    def __init__(self, buf):
        self._sql_fragments = buf

    def write(self, fragment):
        self._sql_fragments.write(fragment)

    def freeze(self):
        return self._sql_fragments.getvalue(), self._bound_variables

class ListStatementPrinter(QueryStatementPrinter):

    def __init__(self, buf):
        super(ListStatementPrinter, self).__init__(buf)
        self._bound_variables = []

    def bind(self, variable):
        self._bound_variables.append(variable)

class DictStatementPrinter(QueryStatementPrinter):

    def __init__(self, buf):
        super(DictStatementPrinter, self).__init__(buf)
        self._bound_variables = {}

    def bind(self, key, variable):
        self._bound_variables[key] = variable

ITERABLE_DATA_TYPES = (list, tuple, dict)

def _resolve_value_in_context_data(ident, data):
    ident_struct = ident.split('.')
    if '' in ident_struct:
        raise KeyError(ident)
    tmp = data
    for e in ident_struct:
        tmp = tmp[e]
    return tmp

class RenderListStatement(object):

    def __init__(self, printer, context, node):
        self.printer = printer
        self.node = node

        # begin compilation
        for n in self.node.get_children():
            n.accept_visitor(self, context)

    def visitLiteral(self, node, context):
        self.printer.write(node.text)
    visitLiteral_strict = visitLiteral_nostrict = visitLiteral
    del visitLiteral

    def visitSubstituteComment_strict(self, node, context):
        try:
            variable = _resolve_value_in_context_data(node.ident, context.data)
        except KeyError, e:
            raise exc.RenderError("No variable feeded: '%s'" % node.ident)
        else:
            self.write_substitute_comment(node, context, variable)

    def visitSubstituteComment_nostrict(self, node, context):
        try:
            variable = _resolve_value_in_context_data(node.ident, context.data)
        except KeyError, e:
            return
        else:
            self.write_substitute_comment(node, context, variable)

    def write_substitute_comment(self, node, context, variable):
        if isinstance(variable, ITERABLE_DATA_TYPES):
            if not len(variable):
                raise exc.RenderError("Binding data should not be empty.")
            self.printer.write('(' + ', '.join(['?' for v in variable]) + ')')
            for v in variable:
                self.printer.bind(v)
        else:
            self.printer.write('?')
            self.printer.bind(variable)

    def visitEmbed_strict(self, node, context):
        if node.ident not in context.data:
            raise exc.RenderError("No variable feeded: '%s'" % node.ident)
        else:
            self.write_embed(node, context)

    def visitEmbed_nostrict(self, node, context):
        if node.ident in context.data:
            self.write_embed(node, context)

    def write_embed(self, node, context):
        variable = context.data[node.ident]
        if isinstance(variable, tree.Node):
            inner_query, inner_bound_variables = compile(variable, '<embedded_node>', context.data,
                                                         parameter_format=list)
            self.printer.write(inner_query)
            for v in inner_bound_variables:
                self.printer.bind(v)
        else:
            self.printer.write(variable)

    def visitIf_strict(self, node, context):
        if node.ident not in context.data:
            raise exc.RenderError("No variable feeded: '%s'" % node.ident)
        else:
            self.write_if(node, context)

    def visitIf_nostrict(self, node, context):
        if node.ident in context.data:
            self.write_if(node, context)

    def write_if(self, node, context):
        if context.data[node.ident]:
            for n in node.get_children():
                n.accept_visitor(self, context)

    def visitFor_strict(self, node, context):
        if node.ident not in context.data:
            raise exc.RenderError("No variable feeded: '%s'" % node.ident)
        else:
            self.write_for(node, context)

    def visitFor_nostrict(self, node, context):
        if node.ident in context.data:
            self.write_for(node, context)

    def write_for(self, node, context):
        alias = node.item
        for_block_context = RenderContext(context.data, strict=context.env['strict'])
        for iterdata in context.data[node.ident]:
            for_block_context.update(**{str(alias): iterdata})
            for n in node.get_children():
                n.accept_visitor(self, for_block_context)

    def visitTip(self, node, context):
        return
    visitTip_strict = visitTip_nostrict = visitTip
    del visitTip

class RenderDictStatement(RenderListStatement):

    def _escape_object_access(self, ident):
        return ident.replace('.', '__dot__')

    def write_substitute_comment(self, node, context, variable):
        if isinstance(variable, ITERABLE_DATA_TYPES) and not len(variable):
            raise exc.RenderError("Binding data should not be empty.")
        if 'for' in context.env:
            for_env = context.env['for']
            alias = for_env['alias']
            if node.ident == alias or node.ident.startswith(alias + '.'):
                ident = node.ident + '_' + str(for_env['count'])
            else:
                ident = node.ident
        else:
            ident = node.ident
        if '.' in ident:
            ident = self._escape_object_access(ident)
        if isinstance(variable, ITERABLE_DATA_TYPES):
            idents = []
            for i, v in enumerate(variable):
                ident_curr = ident + '_' + str(i+1)
                idents.append(':' + ident_curr)
                self.printer.bind(ident_curr, v)
            self.printer.write('(' + ', '.join(idents) + ')')
        else:
            self.printer.write(':' + ident)
            self.printer.bind(ident, variable)

    def write_embed(self, node, context):
        variable = context.data[node.ident]
        if isinstance(variable, tree.Node):
            inner_query, inner_bound_variables = compile(variable, '<embedded_node>', context.data,
                                                         parameter_format=dict)
            self.printer.write(inner_query)
            for ident, v in inner_bound_variables.iteritems():
                self.printer.bind(ident, v)
        else:
            self.printer.write(variable)


    def write_for(self, node, context):
        alias = node.item
        for_env = dict(alias=alias)
        for_block_context = RenderContext(context.data, strict=context.env['strict'])
        for_block_context.env['for'] = for_env
        for i, iterdata in enumerate(context.data[node.ident]):
            for_block_context.update(**{str(alias): iterdata})
            for_env['count'] = i + 1
            for n in node.get_children():
                n.accept_visitor(self, for_block_context)
