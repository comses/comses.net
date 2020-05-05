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
 * Pulled from https://github.com/torchbox/wagtail-markdown on 7/10/2018
 */

/*
 * Used to initialize Easy MDE when Markdown blocks are used in StreamFields
 *
 * https://github.com/Ionaru/easy-markdown-editor#toolbar-icons
 *
 */
function mdeAttach(id) {
        var mde = new EasyMDE({
            element: document.getElementById(id),
            autosave: {
                enabled: true,
                delay: 3000,
                submit_delay: 10000,
                uniqueId: id,
            },
            toolbar: [
                "bold", "italic", "heading", "|",
                "quote", "code", "unordered-list", "ordered-list", "|",
                "horizontal-rule", "link", "image", "table", "|",
                "preview"
            ],
        });
        mde.render();

        mde.codemirror.on("change", function() {
            document.getElementById(id).value = mde.value();
        });
}

/*
 * Used to initialize MDE when MarkdownFields are used on a page.
 */
document.addEventListener("DOMContentLoaded", function() {
    var elements = document.querySelectorAll('.object.markdown textarea');
    Array.prototype.forEach.call(elements, function(element, index) {
        mdeAttach(element.id);
    });
});
