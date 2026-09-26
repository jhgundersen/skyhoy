# SKYHØY 32

Browser game with 32 levels. Live at https://skyhoy.jonh.no.

The whole game is in `public/index.html`. `npm test` checks that the script parses; `npm run build` copies the game to `dist/`.

## Production deployment

Every push to `main` (or manual workflow dispatch) runs the check, builds `dist/`, uploads it by restricted rsync as `skyhoy-deploy`, and verifies the live HTTPS index.

The `/root/website` Docker Compose nginx mounts `/srv/skyhoy` read-only at `/www/skyhoy`. The vhost source is `deploy/skyhoy-https.conf`; the HTTP variant bootstraps the Let's Encrypt certificate.

GitHub configuration uses secrets `DEPLOY_KEY`, `DEPLOY_KNOWN_HOSTS`, and variable `DEPLOY_HOST`. No keys or credentials belong in the repository. Revert a commit on `main` to deploy a previous version.

The global leaderboard (`/api/leaderboard`) is not hosted; the menu button shows an error message, while the personal record is kept in the browser.
