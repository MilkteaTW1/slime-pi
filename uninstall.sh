#!/bin/sh
systemctl --user disable --now slime 2>/dev/null || true
rm -f "$HOME/.config/systemd/user/slime.service" "$HOME/.local/bin/slime"
systemctl --user daemon-reload
echo "Slime stopped. Its memories are still in ~/.slime (delete the folder to let it go)."
