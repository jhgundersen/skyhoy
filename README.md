# SKYHØY 32

Browser game with 32 levels and a global top 100 leaderboard. Live at https://skyhoy.jonh.no.

- `public/index.html`: the whole game. Joachim's commentary portrait (closed and talking frames) is embedded as PNG, cropped from Joachim in `assets/characters.png` in [quest-for-story](https://github.com/jhgundersen/quest-for-story).
- `server/leaderboard.mjs`: leaderboard logic on SQLite via the built-in `node:sqlite` (Node 22.13+). No npm dependencies.
- `server/app.mjs`: HTTP server for `/api/leaderboard` and `/api/health`, with a limit of 40 requests per minute per IP.

`npm test` tests validation, safe retries, top 100 ranking and cleanup. `npm run dev` serves the game and API on http://127.0.0.1:8888 with a local `dev.sqlite`.

## Leaderboard rules

A round is registered at game start (`start`) and can submit one result (`submit`). Retrying an identical submission is safe; a different result for the same round is rejected. Nickname, score, highest level and time are stored. Equal scores are ranked by highest level, then earliest submission. Rounds expire after 24 hours, and unsubmitted rounds are pruned. Scores are computed in the player's browser, so this is an informal leaderboard.

## Production deployment

Every push to `main` (or manual workflow dispatch) runs tests, builds `dist/`, uploads it by restricted rsync as `skyhoy-deploy` to `/srv/skyhoy`, and verifies the live HTTPS index and `/api/health`.

The `/root/website` Docker Compose nginx mounts `/srv/skyhoy` read-only at `/www/skyhoy`. The vhost source is `deploy/skyhoy-https.conf`; `deploy/skyhoy-http.conf` bootstraps the Let's Encrypt certificate. nginx proxies `/api/` to the `skyhoy-leaderboard` container on `website_default` and denies `/server/`.

The leaderboard service is in `deploy/leaderboard/`. Install that directory at `/root/skyhoy-leaderboard/` and start it with `docker compose -f /root/skyhoy-leaderboard/compose.yml up -d`. It runs the uploaded `/srv/skyhoy/server` files from a read-only mount and restarts after each release. The database is in `/srv/skyhoy-data/skyhoy.sqlite` (owned by uid 1000) and is not affected by deploys. Back up that file to keep the leaderboard.

GitHub configuration uses secrets `DEPLOY_KEY`, `DEPLOY_KNOWN_HOSTS`, and variable `DEPLOY_HOST`. No keys or credentials belong in the repository. Revert a commit on `main` to deploy a previous version.
