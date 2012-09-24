from django import http

from hyperadmin.resources.crud.views import CRUDDetailMixin, CRUDCreateView, CRUDListView, CRUDDeleteView, CRUDDetailView, CRUDView


class BoundFile(object):
    def __init__(self, storage, name):
        self.storage = storage
        self.name = name
    
    @property
    def pk(self):
        return self.name
    
    @property
    def url(self):
        return self.storage.url(self.name)
    
    def delete(self):
        return self.storage.delete(self.name)
    
    def exists(self):
        return self.storage.exists(self.name)

class StorageMixin(object):
    def get_upload_link(self, **form_kwargs):
        form_kwargs.update(self.get_form_kwargs())
        link_kwargs = self.get_link_kwargs()
        link_kwargs.update({'form_kwargs': form_kwargs,})
        return self.resource.get_upload_link(**link_kwargs)

class StorageUploadLinkView(StorageMixin, CRUDView):
    view_class = 'change_form'
    
    def get(self, request, *args, **kwargs):
        return self.resource.generate_response(self.get_response_media_type(), self.get_response_type(), self.get_upload_link())
    
    def post(self, request, *args, **kwargs):
        form_kwargs = self.get_request_form_kwargs()
        form_link = self.get_upload_link(**form_kwargs)
        response_link = form_link.submit()
        return self.resource.generate_response(self.get_response_media_type(), self.get_response_type(), response_link)

class StorageCreateView(StorageMixin, CRUDCreateView):
    pass

class StorageListView(StorageMixin, CRUDListView):
    pass

class StorageDetailMixin(StorageMixin, CRUDDetailMixin):
    def get_object(self):
        if not hasattr(self, 'object'):
            self.object = BoundFile(self.resource.resource_adaptor, self.kwargs['path'])
            if not self.object.exists():
                raise http.Http404
        return self.object

class StorageDeleteView(StorageDetailMixin, CRUDDeleteView):
    pass

class StorageDetailView(StorageDetailMixin, CRUDDetailView):
    pass

