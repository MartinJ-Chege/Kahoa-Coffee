#!/usr/bin/env python3
"""Builds the Kahoa blog: blog.html, blog/<slug>.html, blog/feed.xml, blog/og/*.jpg and the blog lines in sitemap.xml.
Run from anywhere:  python3 blog-src/build.py
Posts live in blog-src/posts/<slug>.json, authors in blog-src/authors.json. See README.md."""
import json, glob, os, re, html, urllib.parse, email.utils, datetime
from PIL import Image, ImageDraw, ImageFont, ImageEnhance

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, 'blog-src')
SITE = 'https://kahoa.shop'
BLOG_NAME = 'From the Highlands'
INDEX_TITLE = 'Kahoa Coffee Blog: Stories From the Kenyan Highlands'
INDEX_DESC = 'Stories from our Kenyan coffee-farming family, plus guides to Kenyan coffee and how to brew it. The Kahoa Coffee blog, from Austin, TX.'
GUIDES = [
 ('Guide', 'Kenyan coffee in Austin, Texas', 'Where to buy single-origin Kenyan coffee in Austin, plus cold brew, delivery and the coffee cart.', '/kenyan-coffee-austin.html', '/kahoa-coffee-cart-hero.webp'),
 ('Guide', "Nyeri, Kirinyaga and Murang'a: Kenya's coffee regions", 'Where Kenyan coffee grows, and how altitude, soil and rain shape the cup.', '/kenya-coffee-regions.html', '/kahoa-farm-hero-poster.webp'),
 ('Guide', 'Kenya AA, AB and PB: what the grades mean', 'Kenyan coffee is graded by bean size and shape. Here is how to read the labels.', '/kenya-coffee-grades.html', '/green-kenya-aa.webp'),
 ('Guide', 'How to brew Kenyan coffee at home', 'Pour-over, French press, espresso, cold brew, nitro and spiced cold brew, step by step.', '/brew-guide.html', '/kahoa-brew-hero-poster.webp'),
]

def rd(*p):
    return open(os.path.join(*p), encoding='utf-8').read()
def part(n): return rd(SRC, 'parts', n + '.html')
CSS = rd(SRC, 'base.css') + rd(SRC, 'blog.css').replace('\n', '')
esc = html.escape
def attr(s): return esc(s, quote=True)

authors = json.load(open(os.path.join(SRC, 'authors.json'), encoding='utf-8'))
posts = []
for f in glob.glob(os.path.join(SRC, 'posts', '*.json')):
    p = json.load(open(f, encoding='utf-8')); p['slug'] = os.path.splitext(os.path.basename(f))[0]
    assert p['author'] in authors, 'unknown author ' + p['author']
    posts.append(p)
posts.sort(key=lambda p: (p['date'], p['slug']), reverse=True)

def head(title, desc, url, og, og_alt, kw, typ, ld):
    t, d = esc(title, quote=False), attr(desc)
    return f'''<!doctype html><html lang=en><head><meta charset=UTF-8>
{part('ga')}
<meta content="width=device-width,initial-scale=1.0" name=viewport>
<title>{t}</title>
<meta name="description" content="{d}">
<meta name="keywords" content="{attr(kw)}">
<meta content="index,follow, max-image-preview:large" name=robots>
<link href={url} rel=canonical>
<link rel=alternate type="application/rss+xml" title="Kahoa Coffee Blog" href="{SITE}/blog/feed.xml">
<meta name="author" content="Martin Kibuthu">
<meta property="og:type" content="{typ}"><meta property="og:site_name" content="Kahoa Coffee"><meta property="og:locale" content="en_US"><meta property="og:title" content="{attr(title)}"><meta property="og:description" content="{d}"><meta property="og:url" content="{url}"><meta property="og:image" content="{og}"><meta property="og:image:width" content="1200"><meta property="og:image:height" content="630"><meta property="og:image:alt" content="{attr(og_alt)}">
<meta name="twitter:card" content="summary_large_image"><meta name="twitter:title" content="{attr(title)}"><meta name="twitter:description" content="{d}"><meta name="twitter:image" content="{og}"><meta name="twitter:image:alt" content="{attr(og_alt)}">
<link rel=icon type=image/png href=/kahoalogo.png><link rel=apple-touch-icon href=/kahoalogo.png>
{part('fonts')}
<style>{CSS}</style>
<script type="application/ld+json">{json.dumps(ld, ensure_ascii=False)}</script>
</head><body>
{part('nav')}
'''
TAIL = '\n' + part('footer') + '\n</body></html>\n'
ORG = {"@type": "Organization", "name": "Kahoa Coffee", "url": SITE, "logo": {"@type": "ImageObject", "url": SITE + "/kahoalogo.png"}}
def person(a):
    return {"@type": "Person", "name": a['name'], "jobTitle": a['role'], "url": SITE + a['url'], "image": SITE + a['image']}
def fmt_date(d): 
    x = datetime.date.fromisoformat(d); return x.strftime('%B ') + str(x.day) + x.strftime(', %Y')
def short_date(d):
    x = datetime.date.fromisoformat(d); return x.strftime('%b ') + str(x.day) + x.strftime(', %Y')
def chip(a, extra=''):
    return f'<div class=chip><img src="{a["image"]}" alt="{attr(a["image_alt"])}" width=42 height=42 loading=lazy><div><b>{esc(a["name"])}</b><span>{esc(a["role"])}{extra}</span></div></div>'
def scard(p, a):
    return (f'<a class=scard href="/blog/{p["slug"]}.html"><div class=simg role=img aria-label="{attr(p["card_alt"])}" style="background-image:url({p["card_image"]});background-position:{p["card_position"]}"></div>'
            f'<div class=sbody><span class=tag>{esc(p["category"])} &middot; {short_date(p["date"])}</span><h3>{esc(p["title"])}</h3><p>{esc(p["excerpt"])}</p><span class=go>Read the story</span></div></a>')

# ---------- OG images ----------
def font(bold, size):
    return ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf' if bold else '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', size)
def cover(img, w, h, pos=(0.5, 0.0)):
    r = max(w / img.width, h / img.height); img = img.resize((round(img.width * r) + 1, round(img.height * r) + 1), Image.LANCZOS)
    x = round((img.width - w) * pos[0]); y = round((img.height - h) * pos[1]); return img.crop((x, y, x + w, y + h))
def wrap(d, text, f, maxw):
    lines, cur = [], ''
    for w in text.split():
        t = (cur + ' ' + w).strip()
        if d.textlength(t, font=f) <= maxw: cur = t
        else: lines.append(cur); cur = w
    return lines + [cur]
def og_card(path, title, photo, eyebrow, side=True):
    W, H = 1200, 630; c = Image.new('RGB', (W, H), (28, 14, 6)); d = ImageDraw.Draw(c)
    ph = Image.open(os.path.join(ROOT, photo.lstrip('/'))).convert('RGB')
    if side:
        c.paste(cover(ph, 470, H, (0.5, 0.0)), (0, 0)); x0 = 520
    else:
        bg = ImageEnhance.Brightness(cover(ph, W, H, (0.5, 0.5))).enhance(0.38); c.paste(bg, (0, 0)); x0 = 90
    d.rectangle([x0, 150, x0 + 70, 153], fill=(212, 168, 67))
    d.text((x0, 110), eyebrow.upper(), font=font(False, 22), fill=(212, 168, 67))
    f = font(True, 56); lines = wrap(d, title, f, W - x0 - 70)
    while len(lines) > 4 and f.size > 38: f = font(True, f.size - 4); lines = wrap(d, title, f, W - x0 - 70)
    y = 190
    for ln in lines: d.text((x0, y), ln, font=f, fill=(255, 255, 255)); y += int(f.size * 1.28)
    d.text((x0, H - 70), 'kahoa.shop', font=font(False, 24), fill=(232, 200, 120))
    logo = Image.open(os.path.join(ROOT, 'kahoa-logo.webp')).convert('RGBA').resize((92, 92)); c.paste(logo, (W - 150, H - 128), logo)
    os.makedirs(os.path.dirname(path), exist_ok=True); c.save(path, quality=88)

# ---------- post pages ----------
def build_post(p, others):
    a = authors[p['author']]; url = f'{SITE}/blog/{p["slug"]}.html'
    full_title = f'{p["title"]} | Kahoa Coffee Blog'
    og = f'/blog/og/{p["slug"]}.jpg'; og_card(os.path.join(ROOT, og.lstrip('/')), p['title'], p['card_image'], p['category'])
    words = len(re.sub(r'<[^>]+>', ' ', p['body_html']).split())
    ld = [{"@context": "https://schema.org", "@type": "BlogPosting", "headline": p['title'], "description": p['description'], "datePublished": p['date'], "dateModified": p.get('updated', p['date']),
           "mainEntityOfPage": url, "image": [SITE + og], "inLanguage": "en-US", "wordCount": words, "articleSection": p['category'], "keywords": p['keywords'],
           "author": person(a), "publisher": ORG, "isPartOf": {"@type": "Blog", "name": BLOG_NAME, "url": SITE + "/blog.html"}},
          {"@context": "https://schema.org", "@type": "BreadcrumbList", "itemListElement": [
              {"@type": "ListItem", "position": 1, "name": "Home", "item": SITE + "/"}, {"@type": "ListItem", "position": 2, "name": "Stories", "item": SITE + "/blog.html"},
              {"@type": "ListItem", "position": 3, "name": p['title'], "item": url}]}]
    q = urllib.parse.quote
    share = (f'<div class=share><span>Share</span><a href="https://wa.me/?text={q(p["title"] + " " + url)}" rel=noopener>WhatsApp</a>'
             f'<a href="https://www.facebook.com/sharer/sharer.php?u={q(url)}" rel=noopener>Facebook</a>'
             f'<a href="https://twitter.com/intent/tweet?text={q(p["title"])}&url={q(url)}" rel=noopener>X</a>'
             f'<a href="mailto:?subject={q(p["title"])}&body={q(url)}">Email</a>'
             f'<button type=button onclick="navigator.clipboard&&navigator.clipboard.writeText(\'{url}\').then(()=>{{this.textContent=\'Copied\'}})">Copy link</button></div>')
    abox = (f'<div class=abox><div class=acard><img src="{a["image"]}" alt="{attr(a["image_alt"])}" width=92 height=92 loading=lazy><div><div class=lbl>Written by</div>'
            f'<h3>{esc(a["name"])}</h3><div class=role>{esc(a["role"])}</div><p>{esc(a["bio"])}</p><a href="{a["url"]}">Read our story &rarr;</a></div></div></div>')
    more = ''
    if others: more = '<div class=more><h2>More stories</h2><div class=sgrid>' + ''.join(scard(o, authors[o['author']]) for o in others[:3]) + '</div></div>'
    body = head(full_title, p['description'], url, SITE + og, p['title'], p['keywords'], 'article', ld)
    body += (f'<header class=phero><p class=eyebrow>{esc(p["category"])}</p><h1>{p["h1_html"]}</h1><p class=lede>{esc(p["description"])}</p>'
             f'<div class=byline><img src="{a["image"]}" alt="{attr(a["image_alt"])}" width=52 height=52><div><b>By {esc(a["name"])}</b><span>{esc(a["role"])} &middot; <time datetime="{p["date"]}">{fmt_date(p["date"])}</time> &middot; {p["read_min"]} min read</span></div></div></header>\n'
             f'<div class=crumbs role=navigation aria-label=Breadcrumb><a href=/>Home</a> &rsaquo; <a href=/blog.html>Stories</a> &rsaquo; {p["h1_html"]}</div>\n'
             f'<main class=post><div class=answer><p><strong>In short:</strong> {esc(p["summary"])}</p></div>\n{p["body_html"]}\n</main>\n{share}\n{abox}\n{more}\n'
             '<section class=cta-band><h2>Taste Kenya for yourself</h2><p>Single-origin Kenyan coffee, roasted in Texas and shipped fresh, with free local delivery in Austin.</p><a class=btn-gold href=/shop.html>Shop the coffee</a></section>')
    open(os.path.join(ROOT, 'blog', p['slug'] + '.html'), 'w', encoding='utf-8').write(body + TAIL)

# ---------- index ----------
def build_index():
    url = SITE + '/blog.html'; og = '/blog/og/blog.jpg'
    og_card(os.path.join(ROOT, 'blog/og/blog.jpg'), BLOG_NAME + ': the Kahoa Coffee Blog', '/kahoa-farm-hero-poster.jpg', 'Stories from our Kenyan coffee family', side=False)
    ld = [{"@context": "https://schema.org", "@type": "Blog", "@id": url + "#blog", "name": BLOG_NAME, "description": INDEX_DESC, "url": url, "inLanguage": "en-US", "publisher": ORG,
           "blogPost": [{"@type": "BlogPosting", "headline": p['title'], "url": f"{SITE}/blog/{p['slug']}.html", "datePublished": p['date'], "image": f"{SITE}/blog/og/{p['slug']}.jpg", "author": person(authors[p['author']])} for p in posts]},
          {"@context": "https://schema.org", "@type": "CollectionPage", "name": BLOG_NAME, "url": url, "isPartOf": {"@id": url + "#blog"},
           "mainEntity": {"@type": "ItemList", "itemListElement": [{"@type": "ListItem", "position": i + 1, "url": f"{SITE}/blog/{p['slug']}.html", "name": p['title']} for i, p in enumerate(posts)] +
                          [{"@type": "ListItem", "position": len(posts) + i + 1, "url": SITE + g[3], "name": g[1]} for i, g in enumerate(GUIDES)]}},
          {"@context": "https://schema.org", "@type": "BreadcrumbList", "itemListElement": [{"@type": "ListItem", "position": 1, "name": "Home", "item": SITE + "/"}, {"@type": "ListItem", "position": 2, "name": "Stories", "item": url}]}]
    h = head(INDEX_TITLE, INDEX_DESC, url, SITE + og, BLOG_NAME + ': the Kahoa Coffee Blog', 'Kenyan coffee blog, Kenyan coffee stories, Kenya coffee farm, how to brew Kenyan coffee, Austin coffee roaster, Kahoa Coffee blog', 'website', ld)
    h += ('<header class=bhero><p class=eyebrow>The Kahoa Coffee Blog</p><h1>From the <em>Highlands</em></h1><div class=rule></div>'
          '<p class=lede>Stories from our Kenyan coffee-farming family, and plain-English guides to the coffee in your cup.</p></header>\n')
    f = posts[0]; fa = authors[f['author']]
    h += (f'<a class=feature href="/blog/{f["slug"]}.html"><div class=fimg role=img aria-label="{attr(f["card_alt"])}" style="background-image:url({f["card_image"]});background-position:{f["card_position"]}"></div>'
          f'<div class=ftxt><span class=tag>Latest story &middot; {esc(f["category"])} &middot; {short_date(f["date"])}</span><h2>{esc(f["title"])}</h2><p class=ex>{esc(f["excerpt"])}</p>'
          f'{chip(fa, " &middot; " + str(f["read_min"]) + " min read")}<span class=go>Read the story</span></div></a>\n')
    if len(posts) > 1:
        h += '<div class=wrap><section class=sec><p class=eyebrow>Keep reading</p><h2 class=sh>More stories</h2><div class=sgrid>' + ''.join(scard(p, authors[p['author']]) for p in posts[1:]) + '</div></section></div>\n'
    gc = ''.join(f'<a class=scard href="{g[3]}"><div class=simg style="background-image:url({g[4]})"></div><div class=sbody><span class=tag>{g[0]}</span><h3>{esc(g[1])}</h3><p>{esc(g[2])}</p><span class=go>Read the guide</span></div></a>' for g in GUIDES)
    h += f'<div class=wrap><section class=sec><p class=eyebrow>Start here</p><h2 class=sh>Our Kenyan coffee guides</h2><p class=sub>New to Kenyan coffee? These guides cover where it grows, how it is graded, how to brew it, and where to buy it in Austin.</p><div class=sgrid>{gc}</div></section></div>\n'
    used = []
    for p in posts:
        if p['author'] not in used: used.append(p['author'])
    ac = ''.join(f'<div class=acard><img src="{authors[k]["image"]}" alt="{attr(authors[k]["image_alt"])}" width=128 height=128 loading=lazy><div><h3>{esc(authors[k]["name"])}</h3><div class=role>{esc(authors[k]["role"])}</div><p>{esc(authors[k]["bio"])}</p><a href="{authors[k]["url"]}">Read our story &rarr;</a></div></div>' for k in used)
    h += f'<section class=authors><div class=wrap><p class=eyebrow style="text-align:center">{"Meet the writer" if len(used) == 1 else "Meet the writers"}</p>{ac}</div></section>\n'
    h += '<section class=cta-band><h2>Taste what we write about</h2><p>Single-origin Kenyan coffee, roasted in Texas and shipped fresh, with free local delivery in Austin.</p><a class=btn-gold href=/shop.html>Shop the coffee</a></section>'
    open(os.path.join(ROOT, 'blog.html'), 'w', encoding='utf-8').write(h + TAIL)

# ---------- feed + sitemap ----------
def build_feed():
    items = ''.join(f'<item><title>{esc(p["title"])}</title><link>{SITE}/blog/{p["slug"]}.html</link><guid>{SITE}/blog/{p["slug"]}.html</guid>'
                    f'<pubDate>{email.utils.format_datetime(datetime.datetime.fromisoformat(p["date"] + "T12:00:00+00:00"))}</pubDate><author>info@kahoa.shop ({esc(authors[p["author"]]["name"])})</author><description>{esc(p["description"])}</description></item>' for p in posts)
    open(os.path.join(ROOT, 'blog', 'feed.xml'), 'w', encoding='utf-8').write(
        f'<?xml version="1.0" encoding="UTF-8"?><rss version="2.0"><channel><title>Kahoa Coffee Blog: {BLOG_NAME}</title><link>{SITE}/blog.html</link><description>{esc(INDEX_DESC)}</description><language>en-us</language>{items}</channel></rss>\n')
def build_sitemap():
    path = os.path.join(ROOT, 'sitemap.xml'); s = rd(path)
    s = re.sub(r'\s*<!-- BLOG-START -->.*?<!-- BLOG-END -->', '', s, flags=re.S)
    s = re.sub(r'[ \t]*<url><loc>https://kahoa\.shop/blog[^<]*</loc>.*?</url>\n?', '', s)
    rows = [f'  <url><loc>{SITE}/blog.html</loc><lastmod>{posts[0]["date"]}</lastmod><changefreq>weekly</changefreq><priority>0.7</priority></url>'] + \
           [f'  <url><loc>{SITE}/blog/{p["slug"]}.html</loc><lastmod>{p.get("updated", p["date"])}</lastmod><changefreq>monthly</changefreq><priority>0.6</priority></url>' for p in posts]
    s = s.replace('</urlset>', '  <!-- BLOG-START -->\n' + '\n'.join(rows) + '\n  <!-- BLOG-END -->\n</urlset>')
    open(path, 'w', encoding='utf-8').write(s)

if __name__ == '__main__':
    assert len(INDEX_TITLE) <= 60 and len(INDEX_DESC) <= 160
    for i, p in enumerate(posts):
        assert len(p['description']) <= 160, p['slug'] + ': description too long'
        build_post(p, [o for o in posts if o is not p])
    build_index(); build_feed(); build_sitemap()
    print('built', len(posts), 'post(s)')
