# Convert static site to WordPress theme

This repository includes a small utility to convert a static site (the current `site/` folder) into a simple WordPress theme.

Files added:
- `convert_to_wordpress.py` — main converter script.
- `requirements.txt` — Python dependency list (BeautifulSoup).

How it works:
- Parses `index.html` and extracts head, header, main and footer sections.
- Copies local assets (CSS, JS, images, fonts) into `rmk-theme/assets/`.
- Generates a minimal WordPress theme in `site/rmk-theme/` containing `style.css`, `functions.php`, `header.php`, `footer.php`, `index.php`.

Quick start (Windows PowerShell):
```powershell
python -m pip install -r requirements.txt
python .\convert_to_wordpress.py --site . --out rmk-theme
```

Tailwind CSS (production static build)
------------------------------------

This project previously used the Tailwind CDN. For production we now compile a static CSS file and include it in the theme.

To regenerate the compiled CSS (requires Node.js + npm):

```powershell
npm install
npm run build:css
```

The generated file is written to `rmk-theme/assets/css/tailwind.css` and the theme templates reference that file.

Notes and limitations:
- This script makes best-effort parsing. Complex templates, inline scripts that build DOM, or dynamically-included assets might not be detected.
- The generated theme is minimal. You should adapt `index.php` to include The Loop, create `single.php`, `page.php`, add proper template parts, and secure/enhance enqueues.
- Remote assets (CDN links) are left untouched.

If you'd like, I can extend the script to generate more templates or handle additional HTML files as WordPress page templates.
