"""
This module provides a parse function for parsing RAML with ramlfications,
as well as wrapper classes for the main ramlfications types to make
them more pleasant to work with.
"""
import collections
import six
import ramlfications
import wrapt
from .utils import list_to_dict


def parse(raml_path_or_string):
    root = ramlfications.parse(raml_path_or_string)
    return RootNode(root)


class RootNode(wrapt.ObjectProxy):
    "Wraps a ``ramlfications.raml.RootNode and its contained objects``"
    def __init__(self, wrapped):
        super(RootNode, self).__init__(wrapped)

        self.resources = _map_resources(ResourceNode(r)
                                       for r in wrapped.resources)


class ResourceNode(wrapt.ObjectProxy):
    """Wraps a ``ramlfications.raml.ResourceNode`` to map parameters, bodies and
    responses by a sensible key.
    """
    def __init__(self, wrapped):
        super(ResourceNode, self).__init__(wrapped)

        self.query_params     =  list_to_dict(wrapped.query_params, by='name')
        self.uri_params       =  list_to_dict(wrapped.uri_params, by='name')
        self.base_uri_params  =  list_to_dict(wrapped.base_uri_params, by='name')
        self.form_params      =  list_to_dict(wrapped.form_params, by='name')
        self.headers          =  list_to_dict(wrapped.headers, by='name')
        self.body             =  list_to_dict(wrapped.body, by='mime_type')
        self.responses        =  list_to_dict((Response(r) for r
                                               in (wrapped.responses or [])),
                                               by='code')

    @property
    def example_factory(self):
        """Factory that returns the example value from the method's
        body definition in the RAML.
        """
        try:
            example = self.body[self.content_type].example
        except (KeyError, AttributeError):
            return None
        return lambda: example


class Response(wrapt.ObjectProxy):
    """Wraps a ``ramlfications.raml.Response`` to map headers and body by
    a sensible key."""
    def __init__(self, wrapped):
        super(Response, self).__init__(wrapped)

        self.headers = list_to_dict(wrapped.headers, by='name')
        self.body    = list_to_dict(wrapped.body, by='mime_type')


def _map_resources(resources):
    """Map resources by path and then by method, preserving order except for
    moving DELETEs to the end."""

    resources_by_path = collections.OrderedDict()

    for resource in resources:
        method = resource.method.upper()

        resources_by_path.setdefault(resource.path, collections.OrderedDict())
        resources_by_path[resource.path].setdefault(method, [])
        resources_by_path[resource.path][method] = resource

    for methods in six.itervalues(resources_by_path):
        if 'delete' in methods:
            methods.move_to_end('delete')

    return resources_by_path


