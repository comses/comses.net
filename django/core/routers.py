from rest_framework.routers import Route, SimpleRouter


class AddEditRouter(SimpleRouter):

    """
    A router that includes defaults for simple add / edit url patterns and methods.
    FIXME: on second thought, perhaps these should just live in the regular urls.py
    """
    routes = [
        # add / edit forms
        Route(
            url=r'^{prefix}/add{trailing_slash}$',
            mapping={
                'get': 'add'
            },
            name='{basename}-add',
            initkwargs={'suffix': 'Add'}
        ),
        Route(
            url=r'^{prefix}/{lookup}/edit{trailing_slash}$',
            mapping={
                'get': 'edit'
            },
            name='{basename}-edit',
            initkwargs={'suffix': 'Edit'}
        )
    ] + SimpleRouter.routes


