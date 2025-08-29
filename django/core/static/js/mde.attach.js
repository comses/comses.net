/*
 * vim:sw=4 ts=4 et:
 * Copyright (c) 2015 Torchbox Ltd.
 * felicity@torchbox.com 2015-09-14
 *
 * Permission is granted to anyone to use this software for any purpose,
 * including commercial applications, and to alter it and redistribute it
 * freely. This software is provided 'as-is', without any express or implied
 * warranty.
 *
 * Pulled from https://github.com/torchbox/wagtail-markdown on 2025-08-26
 *
 * Currently using EasyMDE from https://github.com/Ionaru/easy-markdown-editor#toolbar-icons
 *
 */

/*
 * Define window.wagtailMarkdown.options to set EasyMDE options.
 */
window.wagtailMarkdown = window.wagtailMarkdown || {};
window.wagtailMarkdown.options = window.wagtailMarkdown.options || {};

function mdeAttach(id) {
    Object.assign(window.wagtailMarkdown.options, {
        element: document.getElementById(id),
        autofocus: false,
        autoDownloadFontAwesome: true,
        autosave: {
            enabled: false,
        },
        toolbar: [
            "bold", "italic", "heading", "|",
            "quote", "code", "unordered-list", "ordered-list", "|",
            "horizontal-rule", "link", "image", "table", "|",
            "preview"
        ],

    })
    var mde = new EasyMDE(window.wagtailMarkdown.options);
    mde.render();
    // Save the codemirror instance on the original HTML element for later use.
    mde.element.codemirror = mde.codemirror;
    mde.codemirror.on("change", function () {
        document.getElementById(id).value = mde.value();
    });
}

/*
 * Initialize MDE when MarkdownFields are used on in admin panels.
 */
document.addEventListener("wagtail:tab-changed", function () {
    /* NB: original way of registering mde on markdown components
    currently only works on wagtailadmin panels, not on frontend
    probably need to update frontend to manually attach mde into markdown fields
    or use something like https://github.com/vikingmute/vue3-easymde

    var elements = document.querySelectorAll('.object.markdown textarea');
    Array.prototype.forEach.call(elements, function(element, index) {
        mdeAttach(element.id);
    });
    */
    document.querySelectorAll('.CodeMirror').forEach(function (e) {
        setTimeout(
            function () {
                e.CodeMirror.refresh();
            }, 100
        );
    });
});