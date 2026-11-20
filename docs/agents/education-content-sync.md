# Education content synchronization

`django/home/content/education/index.json` and its `content/*.md` files are the
canonical education sources, including the practical `sharing-models` contributor
guide linked from Policies. Thumbnails remain browser assets under
`django/home/static/education/thumbnails/`.

```bash
docker compose exec server ./manage.py sync_education_pages
```

The command validates every entry and internal Markdown file before writing.
It publishes first versions by default, including existing drafts that have never
been published. To keep initial pages unpublished for preview:

```bash
docker compose exec server ./manage.py sync_education_pages --draft
```

Later changes to previously published pages remain drafts. Unpublished pages that
were previously live are not republished automatically. Page IDs, URLs, children,
prior revisions and existing published content are preserved. Unchanged reruns
create no revisions; an unchanged initial draft can be published using its
existing revision. External links do not skip later internal tutorials.

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

The command refuses incompatible page types. It does not delete an old Markdown
education page to change its type, rewrite Resources navigation or remove omitted
content. Reconcile those changes separately in Wagtail.

First publication uses the source-managed content and any preserved editorial
fields. New tutorials publish before a new index. If the index has already been
published, changes to its cards stay in a draft even when a new tutorial is made
live. Publish those index changes in Wagtail to expose the new card. The education
view uses its revision's cards, including in previews, rather than a global query.

## Checks

```bash
make test TEST_ARGS="home.tests.test_policy_page home.tests.test_education_content_sync"
```

Use a disposable database and the repository's containerized test workflow.
Do not point setup or migration operations at a development database that must
be preserved. Compare both live and draft content, retained child IDs, revision
counts, source errors, omitted entries, and an internal tutorial following an
external entry. Check initial publication, `--draft`, and protection of previously
published content, including pages later unpublished by an editor.
