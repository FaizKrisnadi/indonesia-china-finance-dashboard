# Deploy on Render

## Blueprint (recommended)
1. Go to [Render Dashboard](https://dashboard.render.com/).
2. Click **New** -> **Blueprint**.
3. Select this GitHub repo.
4. Render reads `render.yaml` at repo root and creates the web service.
5. Click **Apply** and wait for deploy to finish.

## If using "New Web Service" instead
Use:

- `buildCommand`: `pip install -r requirements.txt`
- `startCommand`: `streamlit run app/Home.py --server.address 0.0.0.0 --server.port $PORT`

## Common failures
- Missing package in `requirements.txt`: add dependency, commit, and redeploy.
- Wrong entrypoint path: verify `app/Home.py` exists with correct casing.
- Build/deploy logs: open your service in Render, then check **Events** and **Logs** for error details.
