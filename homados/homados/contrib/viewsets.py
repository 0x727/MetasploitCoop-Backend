from rest_framework import viewsets, mixins


class ListDestroyViewSet(mixins.DestroyModelMixin,
                         mixins.ListModelMixin,
                         viewsets.GenericViewSet):
    """
    A viewset that provides default `destroy()` and `list()` actions.
    """
    pass


class NoUpdateViewSet(mixins.CreateModelMixin,
                      mixins.DestroyModelMixin,
                      viewsets.ReadOnlyModelViewSet):
    """
    A viewset that provides default `create()`, `retrieve()`, `destroy()` and `list()` actions.
    """
    pass


class NoUpdateRetrieveViewSet(mixins.CreateModelMixin,
                              mixins.DestroyModelMixin,
                              mixins.ListModelMixin,
                              viewsets.GenericViewSet):
    """
    A viewset that provides default `create()`, `destroy()` and `list()` actions.
    """
    pass
