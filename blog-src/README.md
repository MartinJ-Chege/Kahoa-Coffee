# Kahoa blog: how it works

Pages are generated. Do not edit `blog.html` or `blog/*.html` by hand; edit the sources here and run:

    python3 blog-src/build.py

- `posts/<slug>.json`: one file per post (title, description under 160 characters, summary, excerpt, category, date, author, card image, body_html).
- `authors.json`: one entry per writer (name, role, bio, photo path, alt text). To add a writer, add an entry and put their photo in the site root; then set `"author"` in their posts.
- `parts/` and `base.css` are copies of the site header, footer and styles. `blog.css` holds the blog-only styles.
- The build also writes `blog/og/*.jpg` (share-card images), `blog/feed.xml` and the blog lines in `sitemap.xml`.
