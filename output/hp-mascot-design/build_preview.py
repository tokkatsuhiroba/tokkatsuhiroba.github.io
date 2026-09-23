"""Embed artwork into the single-file, offline-loadable UI preview."""
from pathlib import Path
import base64

root = Path(__file__).resolve().parent
html = (root / "page.template.html").read_text()
for token, name in [("__WORLD__", "school-world-retro.png"), ("__MASCOTS__", "mascots.png")]:
    html = html.replace(token, "data:image/png;base64," + base64.b64encode((root / name).read_bytes()).decode())
assert "__WORLD__" not in html and "__MASCOTS__" not in html
(root / "index.html").write_text(html)
print(f"Self-contained UI: {len(html.encode()) / 1024 / 1024:.2f} MB")
