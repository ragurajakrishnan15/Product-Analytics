# Fast GitHub Pages deployment

1. Create a GitHub repository, e.g. `voiceiq-product-analytics`.
2. Push this folder.
3. For a pure static deployment, publish the `site/` directory. The easiest option is to copy `site/*` to the repository root and enable GitHub Pages from the `main` branch `/root`.
4. Your recruiter URL will look like `https://YOUR-USERNAME.github.io/voiceiq-product-analytics/`.

The dashboard loads its JSON from `data/`, so keep `site/data/` together with `index.html`.

Before sharing, replace the `YOUR-USERNAME` GitHub link and `YOUR-EMAIL@example.com` email link in `site/index.html`.
