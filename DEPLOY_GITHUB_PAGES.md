# GitHub Pages deployment

The repository ships with `.github/workflows/pages.yml`, which rebuilds the static snapshot and publishes `site/`
on every push to `main`.

1. Push the repository to `https://github.com/ragurajakrishnan15/Product-Analytics`.
2. One-time: **Settings → Pages → Build and deployment → Source: GitHub Actions**.
3. The workflow runs on the next push (or trigger it from the Actions tab). The dashboard is served at
   `https://ragurajakrishnan15.github.io/Product-Analytics/`.

On a static host the API docs button is hidden, and the customer drawer shows the account profile without the call
timeline (that needs the live API). Everything else, including all statistics, comes from `site/data/snapshot.js`.
