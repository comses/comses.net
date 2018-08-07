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
 * Used to initialize Simple MDE when Markdown blocks are used in StreamFields
 */
function simplemdeAttach(id) {
        var mde = new InscrybMDE({
            element: document.getElementById(id),
            autofocus: false,
            toolbar: [
                "bold", "italic", "heading", "|",
                "quote", "unordered-list", "ordered-list", "|",
                "link", "image", "table", "|",
                "preview"
            ],
        });
        mde.render();

        mde.codemirror.on("change", function() {
            document.getElementById(id).value = mde.value();
        });
}

/*
 * Used to initialize Simple MDE when MarkdownFields are used on a page.
 */
document.addEventListener("DOMContentLoaded", function() {
    var elements = document.querySelectorAll('.object.markdown textarea');
    Array.prototype.forEach.call(elements, function(element, index) {
        simplemdeAttach(element.id);
    });
});
