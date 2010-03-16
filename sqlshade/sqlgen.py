from sqlshade import exc, util
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
        raise exc.RuntimeError("Unsupported parameter format: %s" % parameter_format)

def render_indexed_parameters(node, context):
    printer = IndexedParametersPrinter(util.FastEncodingBuffer())
    RenderIndexedParametersStatement(printer, context, node)
    return printer.freeze()

def render_named_parameters(node, context):
    printer = NamedParametersPrinter(util.FastEncodingBuffer())
    RenderNamedParametersStatement(printer, context, node)
    return printer.freeze()

RENDER_FACTORY = {
    'list': render_indexed_parameters,
    'dict': render_named_parameters,

    list: render_indexed_parameters,
    dict: render_named_parameters,
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

class IndexedParametersPrinter(QueryStatementPrinter):

    def __init__(self, buf):
        super(IndexedParametersPrinter, self).__init__(buf)
        self._bound_variables = []

    def bind(self, variable):
        self._bound_variables.append(variable)

class NamedParametersPrinter(QueryStatementPrinter):

    def __init__(self, buf):
        super(NamedParametersPrinter, self).__init__(buf)
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

class RenderIndexedParametersStatement(object):

    def __init__(self, printer, context, node):
        self.printer = printer
        self.node = node

        # begin compilation
        for n in self.node.get_children():
            n.accept_visitor(self, context)

    def visitLiteral(self, node, context):
        self.printer.write(node.text)
    visitLiteral_strict = visitLiteral
    visitLiteral_nostrict = visitLiteral
    del visitLiteral

    def visitSubstituteComment_strict(self, node, context):
        try:
            variable = _resolve_value_in_context_data(node.ident, context.data)
        except KeyError, e:
            raise exc.RuntimeError("No variable feeded: '%s'" % node.ident)
        else:
            self.write_substitute_comment(node, context, variable)

    def visitSubstituteComment_nostrict(self, node, context):
        try:
            variable = _resolve_value_in_context_data(node.ident, context.data)
        except KeyError, e:
            self.printer.write('/*:%(ident)s*/%(text)s' % dict(ident=node.ident, text=node.text))
        else:
            self.write_substitute_comment(node, context, variable)

    def write_substitute_comment(self, node, context, variable):
        if type(variable) in ITERABLE_DATA_TYPES:
            if not len(variable):
                raise exc.RuntimeError("Binding data should not be empty.")
            self.printer.write('(' + ', '.join(['?' for v in variable]) + ')')
            for v in variable:
                self.printer.bind(v)
        else:
            self.printer.write('?')
            self.printer.bind(variable)

    def visitEmbed_strict(self, node, context):
        if node.ident not in context.data:
            raise exc.RuntimeError("No variable feeded: '%s'" % node.ident)
        else:
            self.write_embed(node, context)

    def visitEmbed_nostrict(self, node, context):
        if node.ident not in context.data:
            self.write_control_comment(node, context)
        else:
            self.write_embed(node, context)

    def write_embed(self, node, context):
        self.printer.write(context.data[node.ident])

    def write_control_comment(self, node, context):
        self.printer.write('/*#%(keyword)s %(text)s*/' % dict(keyword=node.keyword, text=node.text.strip()))
        for n in node.get_children():
            n.accept_visitor(self, context)
        self.printer.write('/*#end%s*/' % node.keyword)

    def visitEval_strict(self, node, context):
        if node.ident not in context.data:
            raise exc.RuntimeError("No variable feeded: '%s'" % node.ident)
        else:
            self.write_eval(node, context)

    def visitEval_nostrict(self, node, context):
        if node.ident not in context.data:
            self.write_control_comment(node, context)
        else:
            self.write_eval(node, context)

    def write_eval(self, node, context):
        template_text = context.data[node.ident]
        sub_lexer = Lexer(template_text)
        sub_node = sub_lexer.parse()
        inner_query, inner_bound_variables = compile(sub_node, '<eval template text>', context.data)
        self.printer.write(inner_query)
        for variable in inner_bound_variables:
            self.printer.bind(variable)

    def visitIf_strict(self, node, context):
        if node.ident not in context.data:
            raise exc.RuntimeError("No variable feeded: '%s'" % node.ident)
        else:
            self.write_if(node, context)

    def visitIf_nostrict(self, node, context):
        if node.ident not in context.data:
            self.write_control_comment(node, context)
        else:
            self.write_if(node, context)

    def write_if(self, node, context):
        if context.data[node.ident]:
            for n in node.get_children():
                n.accept_visitor(self, context)

    def visitFor_strict(self, node, context):
        if node.ident not in context.data:
            raise exc.RuntimeError("No variable feeded: '%s'" % node.ident)
        else:
            self.write_for(node, context)

    def visitFor_nostrict(self, node, context):
        if node.ident not in context.data:
            self.write_control_comment(node, context)
        else:
            self.write_for(node, context)

    def write_for(self, node, context):
        alias = node.item
        for_block_context = RenderContext(context.data, strict=context.env['strict'])
        for iterdata in context.data[node.ident]:
            for_block_context.update(**{str(alias): iterdata})
            for n in node.get_children():
                n.accept_visitor(self, for_block_context)

class RenderNamedParametersStatement(RenderIndexedParametersStatement):

    def write_substitute_comment(self, node, context, variable):
        if type(variable) in ITERABLE_DATA_TYPES and not len(variable):
            raise exc.RuntimeError("Binding data should not be empty.")
        if 'for' in context.env:
            for_env = context.env['for']
            alias = for_env['alias']
            if node.ident == alias or node.ident.startswith(alias + '.'):
                ident = node.ident + '_' + str(for_env['count'])
            else:
                ident = node.ident
        else:
            ident = node.ident
        self.printer.write(':' + ident)
        self.printer.bind(ident, variable)

    def write_eval(self, node, context):
        template_text = context.data[node.ident]
        sub_lexer = Lexer(template_text)
        sub_node = sub_lexer.parse()
        inner_query, inner_bound_variables = compile(sub_node, '<eval template text>', context.data, parameter_format='dict')
        self.printer.write(inner_query)
        for ident, variable in inner_bound_variables.iteritems():
            self.printer.bind(ident, variable)

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
