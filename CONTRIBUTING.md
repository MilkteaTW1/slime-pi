# Contributing

Thanks for helping the slime grow. The code is one Python file with no dependencies, and everything the slime *says* lives in `locales/`.

## Add a language

1. Copy `locales/en.json` to `locales/<tag>.json`, where `<tag>` is a language tag such as `ja`, `ko`, `fr`, `zh-CN` or `pt-BR`.
2. Translate the **values**. Keep the keys. Keep the `{0}`, `{1}` placeholders exactly as they are (you may move them around within the sentence).
3. Set `_name` to your language written in itself, for example `日本語`.
4. Run the checker:

   ```bash
   python tools/check-lang.py
   ```

   It fails if a key is missing or a placeholder changed.
5. Open a pull request. Mention your language and, if you can, whether you tested it on a Pi.

How the slime picks a language: on login it reads the Pi's `LANG` from `/etc/default/locale`, turns `fr_FR.UTF-8` into `fr-FR`, and uses the exact file if it exists, otherwise any file with the same base language (`fr`), otherwise English. To try a language without changing the Pi: `SLIME_LANG=fr_FR.UTF-8 python3 slime.py run`.

Tips for translators:

- The slime is a small, slightly silly creature. Keep the tone playful rather than literal.
- `idle` and `poke` are lists. You can use a different number of lines than English.
- `taste` maps file extensions to a flavour. You can add extensions that matter in your culture; missing ones fall back to `default`.
- Sentences are shown in a speech bubble about 44 characters wide. Longer text is cut.

## Other ways to help

- **New idle thoughts or file-type tastes:** add them to `locales/en.json` (and any language you speak).
- **Test on other boards:** Pi Zero 2 W, Pi 4, Pi 5, other distros. Open an issue with the model, OS and what worked.
- **New moods or growth stages:** the logic is in `decide()` and `STAGES` in `slime.py`, the drawing is in `web/index.html`. Keep the "costs almost nothing" rule: no new background polling.

## Development

```bash
python -m unittest discover -s tests     # unit tests, run anywhere
python tools/check-lang.py               # locale check
python tools/make-gif.py en              # re-record docs/demo.en.gif (needs playwright and ffmpeg)
```

To see the page without a Pi, open `/?demo=en` from any static server that maps `web/` to `/` and `locales/` to `/locales/`. `tools/make-gif.py` contains a tiny one.
