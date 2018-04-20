=========
Discourse
=========

---------
Embedding
---------

Meta Discourse master topic: https://meta.discourse.org/t/embedding-discourse-comments-via-javascript/31963

1. Create a dedicated user for embeds (e.g., `comses`) via ``./launcher enter app`` and the rails console. See
   https://meta.discourse.org/t/how-to-manually-add-users-and-email-in-console-mode/26669 for an example
2. Go to /admin/customize/embedding and create the embeddable host and add embedding settings for Username, Maximum
   number of posts, Crawler settings (pull #discourse-content)

-------------
Rails Console
-------------

Rails has an interactive shell similar to Django's. To reach the shell enter the Discourse container
``./launcher enter app`` and type ``rails c``.


Basic ORM Manipulation
----------------------

Suppose we wanted to all comses owned topics in the code category. We could accomplish that by typing the following
into the Rails console

::

    comses = User.where(username: "comses").first
    code_category = Category.where(name: "Code").first
    code_topics_owned_by_comses = Topic.where(user_id: comses.id, category_id: code_category.id)
    code_topics_owned_by_comses.destroy_all
