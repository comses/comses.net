from unittest.mock import patch

from django.conf import settings
from django.template.loader import get_template
from django.test import SimpleTestCase, override_settings
from django.urls import URLResolver, get_resolver
from djangorestframework_camel_case.render import CamelCaseJSONRenderer
from library import views as library_views
from rest_framework.exceptions import NotAcceptable
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.settings import api_settings
from rest_framework.test import APIRequestFactory
from rest_framework.views import APIView
from rest_framework.viewsets import ViewSet

from core import views as core_views
from core.mixins import HtmlActionRendererMixin

BROWSER_ACCEPT = "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"

# None identifies redirects and files, which do not render a DRF template.
HTML_RESPONSES = {
    core_views.MemberProfileViewSet: {
        "list": "core/member_profiles/list.jinja",
        "retrieve": "core/member_profiles/retrieve.jinja",
        "mark_spam": None,
    },
    core_views.EventViewSet: {
        "list": "core/events/list.jinja",
        "retrieve": "core/events/retrieve.jinja",
        "calendar": "core/events/calendar.jinja",
        "mark_spam": None,
    },
    core_views.JobViewSet: {
        "list": "core/jobs/list.jinja",
        "retrieve": "core/jobs/retrieve.jinja",
        "mark_spam": None,
    },
    library_views.CodebaseViewSet: {
        "list": "library/codebases/list.jinja",
        "retrieve": None,
        "mark_spam": None,
    },
    library_views.CodebaseGitRemoteViewSet: {"list": "library/codebases/git.jinja"},
    library_views.CodebaseReleaseViewSet: {
        "list": None,
        "retrieve": "library/codebases/releases/retrieve.jinja",
        "download": None,
        "request_peer_review": None,
        "notify_reviewers_of_changes": None,
    },
    library_views.CodebaseReleaseShareViewSet: {
        "retrieve": "library/codebases/releases/retrieve.jinja",
        "download": None,
    },
}


def application_api_routes(patterns=None):
    if patterns is None:
        patterns = get_resolver().url_patterns
    for pattern in patterns:
        if isinstance(pattern, URLResolver):
            yield from application_api_routes(pattern.url_patterns)
        else:
            callback = pattern.callback
            view_class = getattr(callback, "cls", None)
            application_modules = tuple(f"{app.partition('.apps.')[0]}." for app in settings.COMSES_APPS)
            if view_class and issubclass(view_class, APIView) and view_class.__module__.startswith(application_modules):
                yield callback


class RendererPolicyTestCase(SimpleTestCase):
    def test_default_is_camel_case_json(self):
        self.assertEqual(api_settings.DEFAULT_RENDERER_CLASSES, [CamelCaseJSONRenderer])

    def test_all_application_routes_obey_renderer_policy(self):
        callbacks = list(application_api_routes())
        # This DRF function is called by a Django view rather than routed directly.
        callbacks.append(library_views._change_peer_review_status)
        seen_views = set()
        for callback in callbacks:
            view_class = callback.cls
            seen_views.add(view_class)
            html_responses = HTML_RESPONSES.get(view_class, {})
            self.assertEqual(set(getattr(view_class, "html_actions", ())), set(html_responses), msg=view_class.__name__)
            actions = getattr(callback, "actions", None)
            methods = (
                dict(actions)
                if actions
                else {method: method for method in view_class.http_method_names if hasattr(view_class, method)}
            )
            methods["options"] = "metadata" if actions else "options"
            if "get" in methods:
                methods["head"] = methods["get"]
            for method, action in methods.items():
                for accept in (None, "*/*", BROWSER_ACCEPT, "application/json", "text/html"):
                    with self.subTest(view=view_class.__name__, action=action, method=method, accept=accept):
                        view = view_class(**callback.initkwargs)
                        view.args, view.kwargs = (), {}
                        if actions:
                            view.action_map = methods
                        headers = {} if accept is None else {"HTTP_ACCEPT": accept}
                        request = APIRequestFactory().generic(method.upper(), "/", **headers)
                        request = view.initialize_request(request)
                        view.request, view.format_kwarg = request, None
                        supports_html = action in html_responses
                        if accept == "text/html" and not supports_html:
                            with self.assertRaises(NotAcceptable):
                                view.perform_content_negotiation(request)
                            continue
                        renderer, media_type = view.perform_content_negotiation(request)
                        expected = "html" if supports_html and accept != "application/json" else "json"
                        self.assertEqual(renderer.format, expected)
                        if expected == "json":
                            # Render success responses without calling any business handler.
                            request.accepted_renderer, request.accepted_media_type = renderer, media_type
                            view.headers = view.default_response_headers
                            response = view.finalize_response(request, Response({"is_pinned": True}))
                            response.render()
                            self.assertEqual(response["Content-Type"], "application/json")
                            self.assertJSONEqual(response.content, {"isPinned": True})
        self.assertTrue(set(HTML_RESPONSES).issubset(seen_views))

    def test_declared_page_templates_exist(self):
        for view_class, actions in HTML_RESPONSES.items():
            for action, template_name in actions.items():
                if template_name:
                    with self.subTest(view=view_class.__name__, action=action):
                        get_template(template_name)
                        # Calendar and git list supply their template on Response.
                        if action in ("list", "retrieve") and view_class != library_views.CodebaseGitRemoteViewSet:
                            view = view_class()
                            view.action = action
                            templates = view.get_template_names()
                            self.assertIn(template_name, [name.replace("//", "/") for name in templates])

    def test_html_only_write_is_rejected_before_handler(self):
        for view_class, action in (
            (core_views.ToggleFollowUser, "post"),
            (library_views.CodebaseReleaseViewSet, "publish"),
        ):
            with self.subTest(view=view_class.__name__), patch.object(view_class, action) as handler:
                callback = view_class.as_view({"post": action}) if action == "publish" else view_class.as_view()
                response = callback(APIRequestFactory().post("/", HTTP_ACCEPT="text/html"))
                response.render()
                self.assertEqual(response.status_code, 406)
                self.assertEqual(response["Content-Type"], "application/json")
                handler.assert_not_called()


class ExampleMixedViewSet(HtmlActionRendererMixin, ViewSet):
    authentication_classes = ()
    permission_classes = (AllowAny,)
    html_actions = ("page",)

    def page(self, request):
        return Response({"page_title": "Example page"}, template_name="example.html")

    def new_api_action(self, request):
        return Response({"is_pinned": True})


@override_settings(
    TEMPLATES=[
        {
            "BACKEND": "django.template.backends.django.DjangoTemplates",
            "OPTIONS": {
                "loaders": [
                    (
                        "django.template.loaders.locmem.Loader",
                        {"example.html": "{{ page_title }}"},
                    )
                ]
            },
        }
    ]
)
class HtmlActionRendererMixinTestCase(SimpleTestCase):
    def test_page_renders_html_and_varies_on_accept(self):
        callback = ExampleMixedViewSet.as_view({"get": "page"})
        for method in ("get", "head"):
            for accept in (None, "*/*", BROWSER_ACCEPT, "text/html"):
                with self.subTest(method=method, accept=accept):
                    headers = {} if accept is None else {"HTTP_ACCEPT": accept}
                    request = APIRequestFactory().generic(method.upper(), "/", **headers)
                    response = callback(request)
                    response.render()
                    self.assertEqual(response.status_code, 200)
                    self.assertEqual(response.content, b"Example page")
                    self.assertIn("Accept", response["Vary"])
                    self.assertTrue(response["Content-Type"].startswith("text/html"))

    def test_page_still_supports_json(self):
        response = ExampleMixedViewSet.as_view({"get": "page"})(
            APIRequestFactory().get("/", HTTP_ACCEPT="application/json")
        )
        response.render()
        self.assertJSONEqual(response.content, {"pageTitle": "Example page"})
        self.assertIn("Accept", response["Vary"])

    def test_new_action_defaults_to_json(self):
        response = ExampleMixedViewSet.as_view({"get": "new_api_action"})(
            APIRequestFactory().get("/", HTTP_ACCEPT=BROWSER_ACCEPT)
        )
        response.render()
        self.assertJSONEqual(response.content, {"isPinned": True})

    def test_page_options_returns_json_metadata(self):
        response = ExampleMixedViewSet.as_view({"get": "page"})(APIRequestFactory().options("/"))
        response.render()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "application/json")
