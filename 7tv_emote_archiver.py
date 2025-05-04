import time
import emote_common as ec


def _log(msg: str) -> None:
    print(f"[{time.strftime('%H:%M:%S')}] {msg}")


def main() -> None:
    _log("7TV archive run started")
    try:
        _, added, same, failed = ec.fetch_7tv_emotes()
        _log(f"7TV: {added} new, {same} unchanged, {failed} failed")
    except Exception as ex:
        _log(f"7TV ERROR: {ex}")
    _log("Done.")


if __name__ == "__main__":
    main()
