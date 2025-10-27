#!/usr/bin/env python3
"""
convert_to_wordpress.py

Simple converter that takes a static site folder (default: current folder)
and generates a basic WordPress theme in `rmk-theme/` inside that folder.

It parses `index.html`, extracts head, header, main and footer parts, copies
assets into the theme's `assets/` folder and updates asset references to use
PHP `get_template_directory_uri()` so the theme is portable.

Usage:
    python convert_to_wordpress.py --site .

Requirements: beautifulsoup4
"""
from __future__ import annotations

import argparse
import os
import re
import shutil
import subprocess
from pathlib import Path
from typing import Dict, Set

try:
    from bs4 import BeautifulSoup, Comment, NavigableString
except Exception as e:
    print("Missing dependency: beautifulsoup4. Install with: pip install -r requirements.txt")
    raise


ASSET_EXTS = {'.css', '.js', '.png', '.jpg', '.jpeg', '.gif', '.svg', '.webp', '.ico', '.woff', '.woff2', '.ttf', '.otf'}


def is_remote(url: str) -> bool:
    if not url:
        return False
    url = url.strip()
    return url.startswith('http://') or url.startswith('https://') or url.startswith('//') or url.startswith('mailto:') or url.startswith('tel:') or url.startswith('#')


def collect_local_assets(soup: BeautifulSoup, site_dir: Path) -> Set[Path]:
    """Find referenced local asset files and return set of Paths relative to site_dir."""
    assets = set()
    # attributes to check
    attr_names = ['src', 'href']
    for tag in soup.find_all():
        for attr in attr_names:
            if tag.has_attr(attr):
                val = tag[attr]
                if not isinstance(val, str):
                    continue
                if is_remote(val):
                    continue
                # ignore mailto, anchors
                # normalize and strip leading ./ or /
                cleaned = val.lstrip('./')
                # only consider files with known extensions
                ext = Path(cleaned).suffix.lower()
                if ext in ASSET_EXTS:
                    candidate = site_dir / cleaned
                    if candidate.exists():
                        assets.add(candidate)
    return assets


def copy_assets(assets: Set[Path], site_dir: Path, dest_assets_dir: Path) -> Dict[str, str]:
    """Copy assets into dest_assets_dir preserving relative structure. Return mapping old_rel -> new_rel (relative to theme root assets dir)."""
    mapping: Dict[str, str] = {}
    for asset in assets:
        try:
            rel = asset.relative_to(site_dir)
        except Exception:
            # fallback: use name only
            rel = Path(asset.name)
        dest_path = dest_assets_dir / rel
        dest_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(asset, dest_path)
        mapping[str(rel).replace('\\', '/')] = str(dest_path.relative_to(dest_assets_dir).as_posix())
    return mapping


def replace_asset_paths_in_html(html: str, mapping: Dict[str, str]) -> str:
    """Replace occurrences of local asset paths in the HTML string with PHP template URI calls pointing to assets folder.

    mapping keys are original relative paths (posix), values are paths inside assets folder.
    """
    # Replace attributes src/href="..." where value matches a key or endswith key
    def repl(match):
        attr = match.group(1)
        quote = match.group(2)
        val = match.group(3)
        key = val.lstrip('./')
        key = key.replace('\\', '/')
        # Find mapping by exact or by basename fallback
        if key in mapping:
            new = mapping[key]
        else:
            # try basename
            basename = Path(key).name
            found = None
            for k, v in mapping.items():
                if Path(k).name == basename:
                    found = v
                    break
            if found:
                new = found
            else:
                return match.group(0)
        # Normalize new so we construct a single /assets/... path consistently
        new = new.lstrip('/')
        # Ensure mapping value is a path relative to the theme's assets directory (e.g. 'css/tailwind.css')
        # and then prefix with /assets/ when generating the PHP template URI.
        php = "<?php echo get_template_directory_uri(); ?>" + "/assets/" + new
        return f'{attr}={quote}' + php + quote

    pattern = re.compile(r'(?i)(src|href)=("|\')([^"\']+)("|\')')
    return pattern.sub(repl, html)


def write_file(path: Path, content: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding='utf-8')


def generate_theme(site_dir: Path, out_dir: Path):
    index_file = site_dir / 'index.html'
    if not index_file.exists():
        raise FileNotFoundError(f'index.html not found in {site_dir}')
    soup = BeautifulSoup(index_file.read_text(encoding='utf-8'), 'html.parser')

    # Remove HTML comments from the parsed document so they aren't copied
    # into generated PHP files (BeautifulSoup represents them as Comment nodes).
    for comment in soup.find_all(string=lambda text: isinstance(text, Comment)):
        comment.extract()

    # Prepare output theme structure
    assets_dir = out_dir / 'assets'
    assets_dir.mkdir(parents=True, exist_ok=True)

    # If a Node build is present (package.json), try to run the Tailwind build to generate a static CSS file.
    pkg = site_dir / 'package.json'
    if pkg.exists():
        # Check for npm/npx availability before attempting to run them
        npm_path = shutil.which('npm')
        npx_path = shutil.which('npx')
        if not npm_path and not npx_path:
            print('Warning: Node.js/npm (or npx) not found in PATH. Skipping automatic Tailwind build.')
            print('To generate the CSS manually, install Node.js and run the following in the site folder (PowerShell):')
            print('  npm install')
            print('  npm run build:css')
        else:
            try:
                # Prefer npm when available (so package scripts run)
                if npm_path:
                    node_modules = site_dir / 'node_modules'
                    if not node_modules.exists():
                        print('node_modules not found — running `npm install` (this may take a while)...')
                        subprocess.run([npm_path, 'install'], cwd=str(site_dir), check=True)
                    # Prefer production build script if available; fall back to build:css
                    print('Attempting production CSS build: `npm run build:css:prod`...')
                    try:
                        subprocess.run([npm_path, 'run', 'build:css:prod'], cwd=str(site_dir), check=True)
                    except subprocess.CalledProcessError:
                        print('`build:css:prod` failed or not present; trying `npm run build:css` instead...')
                        subprocess.run([npm_path, 'run', 'build:css'], cwd=str(site_dir), check=True)
                else:
                    # Fallback to npx invocation of tailwindcss if available
                    print('npm not found, using npx to run tailwindcss directly...')
                    subprocess.run([npx_path, 'tailwindcss', '-i', './src/css/input.css', '-o', './rmk-theme/assets/css/tailwind.css', '--minify'], cwd=str(site_dir), check=True)
            except subprocess.CalledProcessError as e:
                print('Warning: npm/npx build failed with exit code', e.returncode)
            except Exception as e:
                print('Warning: failed to run npm/npx build:', e)

    # Collect assets referenced in the HTML
    assets = collect_local_assets(soup, site_dir)
    mapping = copy_assets(assets, site_dir, assets_dir)
    # Normalize mapping values so they are paths relative to the assets/ dir (no leading 'assets/' or theme-name segments)
    normalized: Dict[str, str] = {}
    for k, v in mapping.items():
        vv = v.lstrip('/')
        # If the mapping somehow contains the output theme folder name (e.g. 'rmk-theme/...'), strip it
        if vv.startswith(out_dir.name + '/'):
            vv = vv[len(out_dir.name) + 1:]
        # If it already starts with 'assets/', strip that so we can consistently prefix '/assets/' later
        if vv.startswith('assets/'):
            vv = vv[len('assets/') :]
        normalized[k] = vv
    mapping = normalized

    # Extract parts
    head_html = ''
    if soup.head:
        # We'll include everything except style/link/script tags that reference remote resources
        # and we'll rewrite local asset references
        head_html = str(soup.head)
        head_html = replace_asset_paths_in_html(head_html, mapping)
        # remove the outer <head> tags because we'll write a full head in header.php
        head_inner = BeautifulSoup(head_html, 'html.parser').head
    head_html = ''.join(str(x) for x in head_inner.contents)

    body = soup.body
    header_html = ''
    main_html = ''
    footer_html = ''

    if body:
        header_tag = body.find('header')
        footer_tag = body.find('footer')
        main_tag = body.find('main')

        if header_tag:
            header_html = replace_asset_paths_in_html(str(header_tag), mapping)
        else:
            # take the first top-level element as header candidate
            first = next((c for c in body.contents if getattr(c, 'name', None)), None)
            if first:
                header_html = replace_asset_paths_in_html(str(first), mapping)

        if main_tag:
            main_html = replace_asset_paths_in_html(str(main_tag), mapping)
        else:
            # everything in body excluding header/footer and skip comments/blank text nodes
            parts = []
            for el in body.contents:
                # skip header/footer tags
                if getattr(el, 'name', None) in ('header', 'footer'):
                    continue
                # skip HTML comments
                if isinstance(el, Comment):
                    continue
                # skip whitespace-only text nodes
                if isinstance(el, NavigableString):
                    if not el.strip():
                        continue
                    parts.append(str(el))
                    continue
                parts.append(str(el))
            main_html = replace_asset_paths_in_html(''.join(parts), mapping)

        if footer_tag:
            footer_html = replace_asset_paths_in_html(str(footer_tag), mapping)

    else:
        # No body - fallback: whole document
        main_html = replace_asset_paths_in_html(str(soup), mapping)

    # Create style.css (WP theme header)
    style_css = f"""/*
Theme Name: RMK Theme
Theme URI: http://example.com/
Author: Tian Hrovat  & Andrej Sušnik
Description: Converted from static site
Version: 1.1.3
*/

/* Add your theme CSS below or edit assets/*.css files copied from the site */
"""
    write_file(out_dir / 'style.css', style_css)

    # Create functions.php - enqueue the theme stylesheet and any copied css/js
    extra_css = [v for k, v in mapping.items() if Path(v).suffix == '.css']
    extra_js = [v for k, v in mapping.items() if Path(v).suffix == '.js']
    enqueue_lines = []
    enqueue_lines.append("\twp_enqueue_style('rmk-style', get_stylesheet_uri());")
    for i, css in enumerate(extra_css):
        enqueue_lines.append(f"\twp_enqueue_style('rmk-extra-{i}', get_template_directory_uri() . '/assets/{css}');")
    for i, js in enumerate(extra_js):
        enqueue_lines.append(f"\twp_enqueue_script('rmk-extra-js-{i}', get_template_directory_uri() . '/assets/{js}', array(), null, true);")

    functions_php = """<?php
function rmk_theme_enqueue() {
%s
}
add_action('wp_enqueue_scripts', 'rmk_theme_enqueue');
""" % ('\n'.join(enqueue_lines))
    write_file(out_dir / 'functions.php', functions_php)

    # header.php
    header_php = """<?php
/**
 * Header for the converted theme
 */
?><!doctype html>
<html <?php language_attributes(); ?>>
<head>
<meta charset="<?php bloginfo( 'charset' ); ?>">
<meta name="viewport" content="width=device-width, initial-scale=1">
<?php wp_head(); ?>
</head>
<body <?php body_class(); ?>>
<?php wp_body_open(); ?>
"""
    # Insert collected head HTML (if any) into head before wp_head() so remote scripts (e.g. Tailwind CDN) are preserved
    if head_html:
        # Place head_html before the wp_head() call
        # Normalize any generated Tailwind path variants to a consistent assets/css/tailwind.css path
        head_html = head_html.replace('rmk-theme/assets/css/tailwind.css', 'assets/css/tailwind.css')
        # BeautifulSoup may escape PHP tags into HTML entities when reparsing; restore them here
        head_html = head_html.replace('&lt;?php', '<?php').replace('?&gt;', '?>')
        # Guard against accidental double '/assets/assets/' sequences
        head_html = head_html.replace('/assets/assets/', '/assets/')
    # Replace any plain-link to assets/css/tailwind.css with a PHP template-uri version
    header_php = header_php.replace("<?php wp_head(); ?>", head_html + "\n<?php wp_head(); ?>")

    # Insert the static header HTML (if any)
    header_php += '\n' + header_html + '\n'

    write_file(out_dir / 'header.php', header_php)

    # footer.php
    footer_php = """<?php
/**
 * Footer for the converted theme
 */
?>
"""
    if footer_html:
        footer_php += '\n' + footer_html + '\n'

    footer_php += "<?php wp_footer(); ?>\n</body>\n</html>\n"
    write_file(out_dir / 'footer.php', footer_php)

    # index.php - simple template that just outputs the main content
    index_php = """<?php
/*
 * Index template generated from static site. Replace with dynamic loop as needed.
 */
get_header();
?>
<main>
%s
</main>
<?php get_footer(); ?>
""" % main_html
    write_file(out_dir / 'index.php', index_php)

    # Optionally copy other static HTML files (like pages) into theme folder as templates or leave in root
    # We'll copy any .html files (except index.html) into theme root as .html for reference
    for html_file in site_dir.glob('*.html'):
        if html_file.name == 'index.html':
            continue
        shutil.copy2(html_file, out_dir / html_file.name)

    print(f"Theme generated at: {out_dir.resolve()}")
    print("Assets copied to: ", assets_dir.resolve())


def main():
    parser = argparse.ArgumentParser(description='Convert static site to a simple WordPress theme')
    parser.add_argument('--site', default='.', help='Path to the static site folder (default: current dir)')
    parser.add_argument('--out', default='rmk-theme', help='Output theme folder name inside the site folder')
    args = parser.parse_args()

    site_dir = Path(args.site).resolve()
    out_dir = (site_dir / args.out).resolve()
    print(out_dir)
    print(site_dir)

    if out_dir.exists():
        confirm = input(f"Output folder {out_dir} already exists. Overwrite? [y/N]: ")
        if confirm.lower() != 'y':
            print('Cancelled')
            return
        shutil.rmtree(out_dir)

    generate_theme(site_dir, out_dir)


if __name__ == '__main__':
    main()
