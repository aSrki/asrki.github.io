#!/usr/bin/env python3
"""
Local CLI tool to create, edit, and delete blog posts for asrki.github.io.

Posts are stored as plain data in blog/posts.json (title, date, text, image
paths). Running any command that changes a post regenerates the static
blog/index.html and blog/<slug>/index.html pages, then optionally commits
and pushes the result to git.

Usage:
    python manage_blog.py new
    python manage_blog.py edit <slug>
    python manage_blog.py delete <slug>
    python manage_blog.py list
    python manage_blog.py build
"""

import argparse
import html
import json
import re
import shutil
import subprocess
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent
BLOG_DIR = ROOT / "blog"
POSTS_JSON = BLOG_DIR / "posts.json"
IMGS_DIR = ROOT / "imgs" / "blog"

SITE_NAME = "Srki's website"
SITE_URL = "https://asrki.github.io"


# ---------------------------------------------------------------- data ----

def load_posts():
    if not POSTS_JSON.exists():
        return []
    with POSTS_JSON.open(encoding="utf-8") as f:
        return json.load(f)


def save_posts(posts):
    BLOG_DIR.mkdir(parents=True, exist_ok=True)
    with POSTS_JSON.open("w", encoding="utf-8") as f:
        json.dump(posts, f, indent=2, ensure_ascii=False)
        f.write("\n")


def find_post(posts, slug):
    for p in posts:
        if p["slug"] == slug:
            return p
    return None


def slugify(title):
    slug = re.sub(r"[^a-z0-9]+", "-", title.lower().strip()).strip("-")
    return slug or "post"


def unique_slug(base, posts, exclude=None):
    existing = {p["slug"] for p in posts if p["slug"] != exclude}
    slug = base
    n = 2
    while slug in existing:
        slug = f"{base}-{n}"
        n += 1
    return slug


# --------------------------------------------------------------- input ----

def read_multiline(label):
    print(f"{label} (type your text, finish with a line containing only: END)")
    lines = []
    while True:
        try:
            line = input()
        except EOFError:
            break
        if line.strip() == "END":
            break
        lines.append(line)
    return "\n".join(lines).strip()


def read_date(default):
    while True:
        raw = input(f"Date [YYYY-MM-DD] (default {default}): ").strip()
        if not raw:
            return default
        try:
            date.fromisoformat(raw)
            return raw
        except ValueError:
            print("Please enter a date like 2026-07-16.")


def copy_images(paths_raw, slug):
    """Copy local image files into imgs/blog/<slug>/ and return web paths."""
    images = []
    if not paths_raw.strip():
        return images

    dest_dir = IMGS_DIR / slug
    dest_dir.mkdir(parents=True, exist_ok=True)

    for raw_path in [p.strip() for p in paths_raw.split(",") if p.strip()]:
        src = Path(raw_path).expanduser()
        if not src.is_file():
            print(f"  Skipping '{raw_path}' — file not found.")
            continue

        dest_name = src.name
        dest = dest_dir / dest_name
        n = 2
        while dest.exists():
            dest = dest_dir / f"{src.stem}-{n}{src.suffix}"
            n += 1

        shutil.copy2(src, dest)
        web_path = f"/imgs/blog/{slug}/{dest.name}"
        alt = input(f"  Alt text for {dest.name} (optional): ").strip()
        images.append({"src": web_path, "alt": alt})
        print(f"  Added {web_path}")

    return images


# ------------------------------------------------------------- render ----

NAV_LINKS = [("/about/", "About Me"), ("/cv/", "CV"), ("/blog/", "Blog")]


def render_nav():
    items = "\n".join(
        f'              <li class="masthead__menu-item">\n'
        f'                <a href="{href}">{label}</a>\n'
        f'              </li>'
        for href, label in NAV_LINKS
    )
    return items


def render_head(title, description, canonical):
    return f"""    <meta charset="utf-8">

    <title>{html.escape(title)} - {SITE_NAME}</title>
    <meta name="description" content="{html.escape(description)}">
    <meta name="author" content="Srđan Apostolović">

    <meta property="og:type" content="website">
    <meta property="og:locale" content="en_US">
    <meta property="og:site_name" content="{SITE_NAME}">
    <meta property="og:title" content="{html.escape(title)}">
    <meta property="og:url" content="{canonical}">
    <meta property="og:description" content="{html.escape(description)}">

    <link rel="canonical" href="{canonical}">

    <meta name="viewport" content="width=device-width, initial-scale=1.0">

    <script type="text/javascript">
      document.documentElement.className = document.documentElement.className.replace(/\\bno-js\\b/g, '') + ' js ';
    </script>

    <!-- For all browsers -->
    <link rel="stylesheet" href="/assets/css/main.css">
    <link rel="stylesheet" href="/assets/css/custom.css">
    <link rel="preload" href="https://cdn.jsdelivr.net/npm/@fortawesome/fontawesome-free@latest/css/all.min.css" as="style" onload="this.onload=null;this.rel='stylesheet'">
    <noscript><link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/@fortawesome/fontawesome-free@latest/css/all.min.css"></noscript>"""


def render_page(title, description, canonical, headline_html, content_html, footer_extra=""):
    return f"""<!doctype html>
<!--
  Static site based on Minimal Mistakes Jekyll Theme 4.26.2 by Michael Rose
  Copyright 2013-2024 Michael Rose - mademistakes.com | @mmistakes
  Free for personal and commercial use under the MIT license
  https://github.com/mmistakes/minimal-mistakes/blob/master/LICENSE
-->

<html lang="en" class="no-js">
  <head>
{render_head(title, description, canonical)}
  </head>

  <body class="layout--single">
    <nav class="skip-links">
      <ul>
        <li><a href="#site-nav" class="screen-reader-shortcut">Skip to primary navigation</a></li>
        <li><a href="#main" class="screen-reader-shortcut">Skip to content</a></li>
        <li><a href="#footer" class="screen-reader-shortcut">Skip to footer</a></li>
      </ul>
    </nav>

    <div class="masthead">
      <div class="masthead__inner-wrap">
        <div class="masthead__menu">
          <nav id="site-nav" class="greedy-nav">
            <a class="site-title" href="/">
              {SITE_NAME}
            </a>
            <ul class="visible-links">
{render_nav()}
            </ul>
            <button class="greedy-nav__toggle hidden" type="button">
              <span class="visually-hidden">Toggle menu</span>
              <div class="navicon"></div>
            </button>
            <ul class="hidden-links hidden"></ul>
          </nav>
        </div>
      </div>
    </div>

    <div class="initial-content">
      <div id="main" role="main">

        <div class="sidebar sticky">
          <div itemscope itemtype="https://schema.org/Person" class="h-card">

            <div class="author__avatar">
              <a href="{SITE_URL}/">
                <img src="/imgs/SrdjanBio.png" alt="Srđan Apostolović" itemprop="image" class="u-photo">
              </a>
            </div>

            <div class="author__content">
              <h3 class="author__name p-name" itemprop="name">
                <a class="u-url" rel="me" href="{SITE_URL}/" itemprop="url">Srđan Apostolović</a>
              </h3>
              <div class="author__bio p-note" itemprop="description">
                <p>Robotics and electronics engineer 🤖</p>
              </div>
            </div>

            <div class="author__urls-wrapper">
              <button class="btn btn--inverse">Follow</button>
              <ul class="author__urls social-icons">
                <li itemprop="homeLocation" itemscope itemtype="https://schema.org/Place">
                  <i class="fas fa-fw fa-map-marker-alt" aria-hidden="true"></i> <span itemprop="name" class="p-locality">Novi Sad, Vojvodina, Serbia</span>
                </li>
                <li><a href="https://github.com/asrki" rel="nofollow noopener noreferrer me" itemprop="sameAs"><i class="fab fa-fw fa-github" aria-hidden="true"></i><span class="label">GitHub</span></a></li>
                <li><a href="mailto:srki.apostolovic@gmail.com" rel="nofollow noopener noreferrer me"><i class="fas fa-fw fa-envelope" aria-hidden="true"></i><span class="label">Email</span></a></li>
              </ul>
            </div>
          </div>
        </div>

        <article class="page" itemscope itemtype="https://schema.org/CreativeWork">
          <meta itemprop="headline" content="{html.escape(title)}">

          <div class="page__inner-wrap">
            <header>
              {headline_html}
            </header>

            <section class="page__content" itemprop="text">
              {content_html}
            </section>

            <footer class="page__meta">
              {footer_extra}
            </footer>
          </div>
        </article>
      </div>
    </div>

    <div id="footer" class="page__footer">
      <footer>
        <div class="page__footer-copyright">&copy; {date.today().year} <a href="{SITE_URL}">{SITE_NAME}</a>. Powered by <a href="https://mademistakes.com/work/minimal-mistakes-jekyll-theme/" rel="nofollow">Minimal Mistakes</a>.</div>
      </footer>
    </div>

    <script src="/assets/js/main.min.js"></script>
  </body>
</html>
"""


def render_paragraphs(text):
    blocks = re.split(r"\n\s*\n", text.strip())
    return "\n".join(
        f"<p>{html.escape(b).replace(chr(10), '<br>')}</p>"
        for b in blocks if b.strip()
    )


def render_images_figure(images):
    if not images:
        return ""
    items = "\n".join(
        f'  <a href="{img["src"]}"><img src="{img["src"]}" alt="{html.escape(img.get("alt", ""))}"></a>'
        for img in images
    )
    return f'<figure class="third">\n{items}\n</figure>'


def render_post_page(post):
    title = post["title"]
    canonical = f'{SITE_URL}/blog/{post["slug"]}/'
    headline_html = (
        f'<h1 id="page-title" class="page__title" itemprop="headline">{html.escape(title)}</h1>\n'
        f'              <p class="page__meta">{html.escape(post["date"])}</p>'
    )
    content_html = render_paragraphs(post.get("text", "")) + "\n\n" + render_images_figure(post.get("images", []))
    footer_extra = '<p><a href="/blog/">&larr; Back to all posts</a></p>'
    return render_page(title, "Robotics engineer", canonical, headline_html, content_html, footer_extra)


def render_index_page(posts):
    sorted_posts = sorted(posts, key=lambda p: p["date"], reverse=True)

    if not sorted_posts:
        list_html = "<p>No posts yet.</p>"
    else:
        items = []
        for p in sorted_posts:
            text = p.get("text", "")
            flat = re.sub(r"\s+", " ", text).strip()
            excerpt = flat[:160] + ("…" if len(flat) > 160 else "")
            images = p.get("images", [])
            thumb = ""
            if images:
                thumb = (
                    '<div class="blog-list-thumb">'
                    f'<img src="{images[0]["src"]}" alt="{html.escape(images[0].get("alt", ""))}">'
                    '</div>'
                )
            items.append(
                '<article class="blog-list-item">\n'
                f"{thumb}\n"
                '  <div class="blog-list-body">\n'
                f'    <h2><a href="/blog/{p["slug"]}/">{html.escape(p["title"])}</a></h2>\n'
                f'    <p class="blog-list-date">{html.escape(p["date"])}</p>\n'
                f"    <p>{html.escape(excerpt)}</p>\n"
                "  </div>\n"
                "</article>"
            )
        list_html = "\n".join(items)

    headline_html = '<h1 id="page-title" class="page__title" itemprop="headline">Blog</h1>'
    return render_page("Blog", "Robotics engineer", f"{SITE_URL}/blog/", headline_html, list_html)


# --------------------------------------------------------------- build ----

def build(posts):
    BLOG_DIR.mkdir(parents=True, exist_ok=True)

    (BLOG_DIR / "index.html").write_text(render_index_page(posts), encoding="utf-8")

    slugs = {p["slug"] for p in posts}
    for p in posts:
        post_dir = BLOG_DIR / p["slug"]
        post_dir.mkdir(parents=True, exist_ok=True)
        (post_dir / "index.html").write_text(render_post_page(p), encoding="utf-8")

    # remove HTML for posts that no longer exist
    for child in BLOG_DIR.iterdir():
        if child.is_dir() and child.name not in slugs:
            shutil.rmtree(child)

    print(f"Built blog/index.html and {len(posts)} post page(s).")


# ----------------------------------------------------------------- git ----

def run_git(args):
    return subprocess.run(["git"] + args, cwd=ROOT, capture_output=True, text=True)


def maybe_push(message, push_flag):
    if push_flag is False:
        return
    if push_flag is None:
        answer = input("Commit and push these changes now? [y/N]: ").strip().lower()
        if answer not in ("y", "yes"):
            print("Skipped git commit/push. Your changes are only on disk for now.")
            return

    print("Staging changes...")
    run_git(["add", "-A"])

    result = run_git(["commit", "-m", message])
    print(result.stdout.strip())
    if result.returncode != 0:
        print(result.stderr.strip())
        if "nothing to commit" in (result.stdout + result.stderr).lower():
            return
        print("Commit failed, not pushing.")
        return

    print("Pushing...")
    result = run_git(["push"])
    print(result.stdout.strip())
    if result.returncode != 0:
        print(result.stderr.strip())
        print("Push failed — you may need to push manually.")
    else:
        print("Pushed.")


# ------------------------------------------------------------ commands ----

def cmd_new(args):
    posts = load_posts()

    title = input("Title: ").strip()
    if not title:
        print("Title is required.")
        sys.exit(1)

    post_date = read_date(date.today().isoformat())
    text = read_multiline("Body text")
    image_paths = input("Image file paths (comma separated, blank for none): ")

    slug = unique_slug(slugify(title), posts)
    images = copy_images(image_paths, slug)

    post = {"slug": slug, "title": title, "date": post_date, "text": text, "images": images}
    posts.append(post)
    save_posts(posts)
    build(posts)

    print(f"\nCreated post '{title}' at /blog/{slug}/")
    maybe_push(f"Add blog post: {title}", args.push)


def cmd_edit(args):
    posts = load_posts()
    post = find_post(posts, args.slug)
    if not post:
        print(f"No post with slug '{args.slug}'.")
        sys.exit(1)

    print(f"Editing '{post['title']}' ({post['slug']})")

    new_title = input(f"Title [{post['title']}]: ").strip()
    if new_title:
        post["title"] = new_title

    post["date"] = read_date(post["date"])

    if input("Replace body text? [y/N]: ").strip().lower() in ("y", "yes"):
        post["text"] = read_multiline("New body text")

    if post.get("images"):
        print("Current images:")
        for i, img in enumerate(post["images"]):
            print(f"  [{i}] {img['src']} (alt: {img.get('alt', '')})")
        remove = input("Remove images? enter indices comma separated, blank to keep all: ").strip()
        if remove:
            drop = {int(i) for i in remove.split(",") if i.strip().isdigit()}
            post["images"] = [img for i, img in enumerate(post["images"]) if i not in drop]

    add_paths = input("Add image file paths (comma separated, blank to skip): ")
    post.setdefault("images", []).extend(copy_images(add_paths, post["slug"]))

    save_posts(posts)
    build(posts)

    print(f"\nUpdated post '{post['title']}'")
    maybe_push(f"Edit blog post: {post['title']}", args.push)


def cmd_delete(args):
    posts = load_posts()
    post = find_post(posts, args.slug)
    if not post:
        print(f"No post with slug '{args.slug}'.")
        sys.exit(1)

    if input(f"Delete '{post['title']}' ({post['slug']})? [y/N]: ").strip().lower() not in ("y", "yes"):
        print("Cancelled.")
        return

    posts = [p for p in posts if p["slug"] != post["slug"]]
    save_posts(posts)
    build(posts)

    image_dir = IMGS_DIR / post["slug"]
    if image_dir.exists():
        shutil.rmtree(image_dir)

    print(f"Deleted post '{post['title']}'")
    maybe_push(f"Delete blog post: {post['title']}", args.push)


def cmd_list(args):
    posts = sorted(load_posts(), key=lambda p: p["date"], reverse=True)
    if not posts:
        print("No posts yet.")
        return
    for p in posts:
        print(f"{p['date']}  {p['slug']:30s} {p['title']}")


def cmd_build(args):
    posts = load_posts()
    build(posts)


# ------------------------------------------------------------------ cli ----

def main():
    parser = argparse.ArgumentParser(description="Manage blog posts for asrki.github.io")
    sub = parser.add_subparsers(dest="command", required=True)

    def add_push_flag(p):
        group = p.add_mutually_exclusive_group()
        group.add_argument("--push", dest="push", action="store_true", default=None, help="commit & push without asking")
        group.add_argument("--no-push", dest="push", action="store_false", help="never commit/push")

    p_new = sub.add_parser("new", help="create a new post")
    add_push_flag(p_new)
    p_new.set_defaults(func=cmd_new)

    p_edit = sub.add_parser("edit", help="edit an existing post")
    p_edit.add_argument("slug")
    add_push_flag(p_edit)
    p_edit.set_defaults(func=cmd_edit)

    p_delete = sub.add_parser("delete", help="delete a post")
    p_delete.add_argument("slug")
    add_push_flag(p_delete)
    p_delete.set_defaults(func=cmd_delete)

    p_list = sub.add_parser("list", help="list all posts")
    p_list.set_defaults(func=cmd_list)

    p_build = sub.add_parser("build", help="regenerate blog HTML without changing content")
    p_build.set_defaults(func=cmd_build)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
