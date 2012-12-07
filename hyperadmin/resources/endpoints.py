from django.conf.urls.defaults import url
from django.views.generic import View

from hyperadmin.hyperobjects import Link, LinkCollection, LinkCollectionProvider
from hyperadmin.states import EndpointState, SESSION_STATE


class LinkPrototype(object):
    def __init__(self, endpoint, link_kwargs={}):
        self.endpoint = endpoint
        self.link_kwargs = link_kwargs
    
    @property
    def resource(self):
        return self.endpoint.resource
    
    @property
    def state(self):
        return self.endpoint.state
    
    @property
    def common_state(self):
        return self.endpoint.common_state
    
    def show_link(self, **kwargs):
        return True
    
    def get_form_class(self):
        return self.endpoint.get_form_class()
    
    def get_form_kwargs(self, **kwargs):
        return self.endpoint.get_form_kwargs(**kwargs)
    
    def get_link_kwargs(self, **kwargs):
        kwargs.update(self.link_kwargs)
        kwargs['form_kwargs'] = self.get_form_kwargs(**kwargs)
        kwargs.setdefault('endpoint', self.endpoint)
        assert self.endpoint.state, 'link creation must come from a dispatched endpoint'
        return kwargs
    
    def get_link(self, **link_kwargs):
        link_kwargs = self.get_link_kwargs(**link_kwargs)
        link = Link(**link_kwargs)
        return link
    
    def handle_submission(self, link, submit_kwargs):
        form = link.get_form(**submit_kwargs)
        if form.is_valid():
            instance = form.save()
            resource_item = self.endpoint.get_resource_item(instance)
            return self.on_success(resource_item)
        return link.clone(form=form)
    
    def on_success(self, item=None):
        if item is not None:
            return item.get_link()
        return self.endpoint.get_resource_link()
    
    def get_url(self, **kwargs):
        return self.endpoint.get_url(**kwargs)

class BaseEndpoint(object):
    state = None #for this particular endpoint
    #TODO find a better name for "common_state"
    common_state = None #shared by endpoints of the same resource
    session_state = SESSION_STATE #state representing the current request
    
    state_class = EndpointState
    
    def __init__(self, **kwargs):
        super(BaseEndpoint, self).__init__(**kwargs)
        self.common_state = self.get_common_state()
        self.initialize_state()
    
    def get_common_state(self):
        return None
    
    def get_state_data(self):
        return {}
    
    def get_meta(self):
        return {}
    
    def get_state_kwargs(self):
        kwargs = {
            'endpoint': self,
            'data':self.get_state_data(),
            'meta':{},
        }
        if self.common_state is not None:
            kwargs['substates'] = [self.common_state]
        return kwargs
    
    def get_state_class(self):
        return self.state_class
    
    def initialize_state(self, **data):
        kwargs = self.get_state_kwargs()
        kwargs['data'].update(data)
        self.state = self.get_state_class()(**kwargs)
        self.state.meta = self.get_meta()
        return self.state
    
    def reverse(self, *args, **kwargs):
        return self.state.reverse(*args, **kwargs)
    
    #urls
    
    def get_base_url_name(self):
        raise NotImplementedError
    
    def get_url(self, **kwargs):
        return self.reverse(self.get_url_name(), **kwargs)
    
    def create_link_collection(self):
        return LinkCollection(endpoint=self)
    
    #link_prototypes

class Endpoint(BaseEndpoint, View):
    """
    Represents an API endpoint
    
    Behaves like a class based view
    Initialized originally without a state; should endpoint be a class based view that pumps to another?
    """
    name_suffix = None
    view_class = None
    url_suffix = None
    resource = None
    
    def __init__(self, **kwargs):
        self._init_kwargs = kwargs
        self.links = LinkCollectionProvider(self, kwargs['resource'].links)
        super(Endpoint, self).__init__(**kwargs)
    
    @property
    def link_prototypes(self):
        return self.resource.link_prototypes
    
    def dispatch(self, request, *args, **kwargs):
        """
        Endpoint simply dispatches to a defined class based view
        """
        #CONSIDER does it make sense to proxy? perhaps we should just merge
        #can we get the view state?
        self.request = request
        handler = self.get_internal_view()
        return handler(request, *args, **kwargs)
    
    def get_view_kwargs(self):
        kwargs = self.resource.get_view_kwargs()
        kwargs.update({'endpoint': self,
                       'state': self.state,})
        return kwargs
    
    def get_view_class(self):
        return self.view_class
    
    def get_internal_view(self):
        init = self.get_view_kwargs()
        klass = self.get_view_class()
        assert klass
        return klass.as_view(**init)
    
    def get_view(self, **kwargs):
        kwargs.update(self._init_kwargs)
        view = type(self).as_view(**kwargs)
        #allow for retreiving the endpoint from url patterns
        view.endpoint = self
        #thus allowing us to do: myview.endpoint.get_view(**some_new_kwargs)
        return view
    
    def get_base_url_name(self):
        return self.resource.get_base_url_name()
    
    def get_url_name(self):
        return self.get_base_url_name() + self.name_suffix
    
    def get_url_suffix(self):
        return self.url_suffix
    
    def get_url_object(self):
        view = self.get_view()
        return url(self.get_url_suffix(), view, name=self.get_url_name(),)
    
    def get_url(self, **kwargs):
        return self.reverse(self.get_url_name(), **kwargs)
    
    #TODO better name => get_internal_links?
    def get_links(self):
        """
        return a dictionary of endpoint links
        """
        return {}
    
    def get_resource_item(self, instance):
        return self.resource.get_resource_item(instance, endpoint=self)
    
    def get_instances(self):
        return self.resource.get_instances()
    
    def get_resource_items(self):
        instances = self.get_instances()
        return [self.get_resource_item(instance) for instance in instances]
    
    def get_common_state(self):
        return self.resource.state
    
    def get_resource_link(self, **kwargs):
        link_kwargs = {'rel':'self',
                       'prompt':self.resource.get_prompt(),}
        link_kwargs.update(kwargs)
        return self.link_prototypes['list'].get_link(**kwargs)
    
    def get_item_url(self, item):
        return self.resource.get_item_url(item)
    
    def get_form_class(self):
        return self.resource.get_form_class()
    
    def get_form_kwargs(self, **kwargs):
        form_kwargs = kwargs.get('form_kwargs', None) or {}
        form_kwargs['item'] = kwargs.get('item', None)
        return self.resource.get_form_kwargs(**form_kwargs)
    
    def get_namespaces(self):
        return self.resource.get_namespaces()
    
    def get_item_namespaces(self, item):
        return self.resource.get_item_namespaces(item=item)
    
    def get_item_link(self, item):
        return self.resource.get_item_link(item=item)
