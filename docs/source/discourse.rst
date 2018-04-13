=========
Discourse
=========

---------
Embedding
---------

Meta Discourse master topic: https://meta.discourse.org/t/embedding-discourse-comments-via-javascript/31963

1. Create a dedicated user for embeds (e.g., `comses`) via `./launcher enter app` and the rails console. See https://meta.discourse.org/t/how-to-manually-add-users-and-email-in-console-mode/26669 for an example
2. Go to /admin/customize/embedding and create the embeddable host and add embedding settings for Username, Maximum number of posts, Crawler settings (pull #discourse-content)