# Education content synchronization

`django/home/content/education/index.json` and its `content/*.md` files are the
canonical education sources. Thumbnails remain browser assets under
`django/home/static/education/thumbnails/`.

```bash
docker compose exec server ./manage.py sync_education_pages
```

The command validates every entry and internal Markdown file before creating
draft revisions. It preserves page IDs, URLs,
children, prior revisions, and published content. Repeating a sync against a
matching latest draft creates no new revision. External links do not prevent
later internal tutorials from being synchronized.

## Managed content

- The index page title, heading, and summary come from the command constants.
- Internal tutorial titles, headings, descriptions, and bodies come from the
  index and Markdown files. Other CMS fields remain editorially managed.
- Cards are matched by URL within the education page. Their titles, summaries,
  categories, tags, and order come from the index. Existing thumbnails remain;
  a matching PNG is imported only for a card without a thumbnail.
- Omitted cards are retained after the source-listed cards. Omitted tutorial
  pages remain in place. A changed external URL creates a new card; review the
  old card explicitly rather than relying on omission to remove it.

The command refuses incompatible existing page types. It does not delete an old
Markdown education page to change its type, rewrite Resources navigation, publish
revisions, or remove omitted content. Reconcile those changes separately in Wagtail.

Review and publish new tutorial pages before publishing index cards that link to
them. Use Wagtail previews to check pending index-card and tutorial-body changes.
The education view uses its own revision's cards, including in previews, rather
than a global query of saved cards.

## Checks

```bash
make test TEST_ARGS="home.tests.test_policy_page home.tests.test_education_content_sync"
```

Use a disposable database and the repository's containerized test workflow.
Do not point setup or migration operations at a development database that must
be preserved. Compare both live and draft content, retained child IDs, revision
counts, source errors, omitted entries, and an internal tutorial following an
external entry. No live education content is changed by this refactor alone.
