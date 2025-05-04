import argparse, time
import emote_common as ec


def _log(msg: str) -> None:
    print(f"[{time.strftime('%H:%M:%S')}] {msg}")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--source",
        choices=("7tv", "official", "both"),
        default="both",
        help="What to refresh (default = both)",
    )
    source = ap.parse_args().source

    _log(f"Archive run started (source = {source})")

    if source in ("7tv", "both"):
        try:
            _, added, same, failed = ec.fetch_7tv_emotes()
            _log(f"7TV:     {added} new, {same} unchanged, {failed} failed")
        except Exception as ex:
            _log(f"7TV ERROR: {ex}")

    if source in ("official", "both"):
        try:
            _, added, same, failed = ec.fetch_twitch_emotes()
            _log(f"Twitch:  {added} new, {same} unchanged, {failed} failed")
        except Exception as ex:
            _log(f"Twitch ERROR: {ex}")

    _log("Done.")


if __name__ == "__main__":
    main()
