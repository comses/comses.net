from django.forms import Media, Textarea
from wagtail.admin.staticfiles import versioned_static


class MarkdownTextarea(Textarea):
    def build_attrs(self, *args, **kwargs):
        attrs = super().build_attrs(*args, **kwargs)
        attrs["data-controller"] = "mde-controller"
        return attrs

    def render(self, name, value, attrs=None, renderer=None):
        # extract the raw content of markupfield into the markdown field
        if hasattr(value, "raw"):
            value = value.raw
        return super().render(name, value, attrs, renderer)

    @property
    def media(self):
        return Media(
            css={
                "all": (
                    "https://unpkg.com/easymde/dist/easymde.min.css",
                    versioned_static("css/easymde.custom.css"),
                )
            },
            js=(
                # FIXME: can we pull this from node dependencies somehow
                "https://unpkg.com/easymde/dist/easymde.min.js",
                versioned_static("js/mde.attach.js"),
                # load controller js
                versioned_static("js/mde-controller.js"),
            ),
        )
