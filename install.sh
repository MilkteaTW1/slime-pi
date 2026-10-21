#!/bin/sh
# Install the slime as a user service (no sudo needed, except for the optional linger step).
set -e
DIR="$(cd "$(dirname "$0")" && pwd)"
mkdir -p "$HOME/.config/systemd/user" "$HOME/.local/bin"
sed "s|@DIR@|$DIR|" "$DIR/systemd/slime.service" > "$HOME/.config/systemd/user/slime.service"
printf '#!/bin/sh\nexec python3 "%s/slime.py" look\n' "$DIR" > "$HOME/.local/bin/slime"
chmod +x "$HOME/.local/bin/slime"
systemctl --user daemon-reload
systemctl --user enable --now slime
loginctl enable-linger "$USER" 2>/dev/null || echo "Tip: run 'sudo loginctl enable-linger $USER' so the slime keeps living after you log out."
echo "Done. Open http://$(hostname).local:8077 or run: slime"
