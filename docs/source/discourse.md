# Discourse

## Embedding

Meta Discourse master topic: <https://meta.discourse.org/t/embedding-discourse-comments-via-javascript/31963>

currently using DiscourseEmbed to link to our Discourse forums as an inline iframe on every CodebaseRelease detail page.

some residual issues with the `comses` user being added as the author on topics that should hopefully be addressed in
the future after explicit and automatic comses user <-> discourse user sync via Discourse's `sync_sso` endpoint.

## Rails Console

Enter the rails console via `./launcher enter app` and `rails c`.

### Basic ORM Manipulation

Find all comses owned topics in the code category:

```ruby
comses = User.where(username: "comses").first
code_category = Category.where(name: "Code").first
code_topics_owned_by_comses = Topic.where(user_id: comses.id, category_id: code_category.id)
code_topics_owned_by_comses.destroy_all # don't actually do this
```
