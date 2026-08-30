#!/usr/bin/env python3
"""Extract the OAuth2 client credentials from a copy of the Cookidoo Android app.

The credentials are not distributed with this library (see docs/oauth-client.md),
they have to be read out of an APK you obtained yourself. This script does that
without any third party tooling: it collects the string constants an APK carries
(dex string pools, the resource string pool, and plain text assets) and reports
the ones that make up an OAuth2 client id, client secret and redirect uri.

The client id and secret are usually recovered exactly, because the app ships
the ready made HTTP Basic header for the token endpoint, and that decodes to
``client_id:client_secret``. Only when no such pair is found does the script
fall back to ranking individual strings heuristically.

Usage
-----
    ./scripts/extract-oauth-client.py cookidoo.apk
    ./scripts/extract-oauth-client.py cookidoo.apk --env >> .env
    ./scripts/extract-oauth-client.py cookidoo.apk --grep 'grant'

Check the output before use: an APK carries the credentials of every
environment it can talk to, not just production. Use --grep to search the
extracted strings yourself when the heuristics come up short.
"""

import argparse
import base64
import binascii
from pathlib import Path
import re
import sys
from typing import NamedTuple
import zipfile

# Chunk type of a ResStringPool, used by resources.arsc and binary XML alike.
RES_STRING_POOL_TYPE = 0x0001
UTF8_FLAG = 1 << 8

# Offsets into the dex header of the string id table.
DEX_STRING_IDS_SIZE_OFF = 0x38
DEX_STRING_IDS_OFF_OFF = 0x3C

# Schemes that are never an app's private redirect target.
COMMON_SCHEMES = frozenset(
    {"http", "https", "ws", "wss", "file", "content", "market", "mailto", "tel"}
)

# Keys a structured config may use for each credential.
CONFIG_KEYS: dict[str, tuple[str, ...]] = {
    "client_id": ("client_id", "clientid", "oauthclientid", "authclientid"),
    "client_secret": (
        "client_secret",
        "clientsecret",
        "oauthclientsecret",
        "authclientsecret",
    ),
    "redirect_uri": (
        "redirect_uri",
        "redirecturi",
        "redirect_url",
        "redirecturl",
        "callbackurl",
    ),
}

REDIRECT_RE = re.compile(r"^([a-zA-Z][a-zA-Z0-9+.\-]*)://[^\s\"'<>]*$")
CLIENT_ID_RE = re.compile(r"^[a-z0-9]+(?:[-_.][a-z0-9]+)*$")
# A secret has no separators; allowing them would drown the field in the
# ``methodName-hash`` symbols the Kotlin compiler emits by the thousand.
SECRET_RE = re.compile(r"^[A-Za-z0-9]{16,64}$")
BASE64_RE = re.compile(r"^(?:Basic\s+)?([A-Za-z0-9+/]{16,}={0,2})$")
UPPER_RUN_RE = re.compile(r"[A-Z]{2,}")
CLIENT_ID_HINTS = ("android", "mobile", "ios", "app", "client", "native")


class Candidate(NamedTuple):
    """A possible credential value with the reason it was picked."""

    value: str
    score: int
    source: str


class ClientPair(NamedTuple):
    """A client id and secret recovered together from one Basic auth header."""

    client_id: str
    client_secret: str
    encoded: str


def _uleb128(data: bytes, pos: int) -> tuple[int, int]:
    """Read an unsigned LEB128 integer, returning the value and the new position."""
    result = shift = 0
    while True:
        byte = data[pos]
        pos += 1
        result |= (byte & 0x7F) << shift
        if not byte & 0x80:
            return result, pos
        shift += 7


def dex_strings(data: bytes) -> list[str]:
    """Return every string constant in a classes.dex string pool."""
    if not data.startswith(b"dex\n") or len(data) < DEX_STRING_IDS_OFF_OFF + 4:
        return []
    count = int.from_bytes(data[DEX_STRING_IDS_SIZE_OFF:][:4], "little")
    table = int.from_bytes(data[DEX_STRING_IDS_OFF_OFF:][:4], "little")
    strings = []
    for i in range(count):
        entry = table + i * 4
        if entry + 4 > len(data):
            break
        offset = int.from_bytes(data[entry : entry + 4], "little")
        if offset >= len(data):
            continue
        # utf16 length prefix, then MUTF-8 bytes up to a NUL terminator
        _, start = _uleb128(data, offset)
        end = data.find(b"\x00", start)
        if end == -1:
            continue
        strings.append(data[start:end].decode("utf-8", errors="replace"))
    return strings


def _byte_len(data: bytes, pos: int) -> tuple[int, int]:
    """Read a ResStringPool length prefix of one or two bytes."""
    first = data[pos]
    if first & 0x80:
        return ((first & 0x7F) << 8) | data[pos + 1], pos + 2
    return first, pos + 1


def _pool_string(data: bytes, offset: int, utf8: bool) -> str:
    """Decode a single entry of a ResStringPool at an absolute offset."""
    if utf8:
        # Two length prefixes: the utf16 length, then the byte length.
        _, pos = _byte_len(data, offset)
        size, pos = _byte_len(data, pos)
        return data[pos : pos + size].decode("utf-8", errors="replace")
    length = int.from_bytes(data[offset : offset + 2], "little")
    pos = offset + 2
    if length & 0x8000:
        length = ((length & 0x7FFF) << 16) | int.from_bytes(
            data[pos : pos + 2], "little"
        )
        pos += 2
    return data[pos : pos + length * 2].decode("utf-16-le", errors="replace")


def string_pool_strings(data: bytes) -> list[str]:
    """Return the strings of every ResStringPool chunk found in a blob.

    Works for both ``resources.arsc`` and binary XML such as AndroidManifest.xml,
    which embed the same chunk format.
    """
    strings: list[str] = []
    pos = 0
    limit = len(data)
    while pos + 8 <= limit:
        chunk_type = int.from_bytes(data[pos : pos + 2], "little")
        chunk_size = int.from_bytes(data[pos + 4 : pos + 8], "little")
        if chunk_size < 8 or pos + chunk_size > limit:
            pos += 4
            continue
        if chunk_type == RES_STRING_POOL_TYPE:
            strings.extend(_parse_string_pool(data[pos : pos + chunk_size]))
            pos += chunk_size
            continue
        # Descend into container chunks (their header is followed by children).
        header_size = int.from_bytes(data[pos + 2 : pos + 4], "little")
        pos += header_size if 8 <= header_size < chunk_size else chunk_size
    return strings


def _parse_string_pool(chunk: bytes) -> list[str]:
    """Parse one ResStringPool chunk into its list of strings."""
    if len(chunk) < 28:
        return []
    count = int.from_bytes(chunk[8:12], "little")
    flags = int.from_bytes(chunk[16:20], "little")
    strings_start = int.from_bytes(chunk[20:24], "little")
    utf8 = bool(flags & UTF8_FLAG)
    strings = []
    for i in range(count):
        entry = 28 + i * 4
        if entry + 4 > len(chunk):
            break
        offset = strings_start + int.from_bytes(chunk[entry : entry + 4], "little")
        if offset >= len(chunk):
            continue
        try:
            strings.append(_pool_string(chunk, offset, utf8))
        except (IndexError, ValueError):
            continue
    return strings


def _config_candidates(name: str, blob: str) -> dict[str, str]:
    """Pull credentials out of a plain text asset that names them explicitly."""
    found: dict[str, str] = {}
    for field, keys in CONFIG_KEYS.items():
        for key in keys:
            match = re.search(
                rf'["\']?{re.escape(key)}["\']?\s*[:=]\s*["\']([^"\']{{3,200}})["\']',
                blob,
                re.IGNORECASE,
            )
            if match:
                found[field] = match.group(1)
                break
    if found:
        print(f"  config-like asset {name}: {sorted(found)}", file=sys.stderr)
    return found


def collect_strings(apk: Path) -> tuple[list[str], dict[str, str]]:
    """Collect all string constants and any explicitly named credentials."""
    strings: list[str] = []
    explicit: dict[str, str] = {}
    with zipfile.ZipFile(apk) as zf:
        for info in zf.infolist():
            name = info.filename
            if info.is_dir() or info.file_size > 128 * 1024 * 1024:
                continue
            data = zf.read(name)
            if name.startswith("classes") and name.endswith(".dex"):
                strings.extend(dex_strings(data))
            elif name == "resources.arsc" or name.endswith(".xml"):
                strings.extend(string_pool_strings(data))
            elif name.startswith(("assets/", "res/raw/")) and info.file_size < 2**20:
                blob = data.decode("utf-8", errors="ignore")
                strings.extend(re.findall(r'["\']([^"\'\n]{3,200})["\']', blob))
                for key, value in _config_candidates(name, blob).items():
                    explicit.setdefault(key, value)
    return strings, explicit


def basic_auth_pairs(strings: list[str]) -> list[ClientPair]:
    """Recover ``client_id:client_secret`` pairs from embedded Basic auth headers.

    Apps commonly ship the ready made ``Authorization`` value for the token
    endpoint rather than building it at runtime, which hands us both halves of
    the client credentials exactly instead of by guesswork.
    """
    pairs: dict[str, ClientPair] = {}
    for value in strings:
        match = BASE64_RE.match(value.strip())
        if not match:
            continue
        try:
            decoded = base64.b64decode(match.group(1), validate=True).decode("ascii")
        except (binascii.Error, UnicodeDecodeError, ValueError):
            continue
        client_id, sep, secret = decoded.partition(":")
        if not sep or not client_id or not secret:
            continue
        if not CLIENT_ID_RE.match(client_id) or not SECRET_RE.match(secret):
            continue
        pairs.setdefault(decoded, ClientPair(client_id, secret, value))
    return sorted(pairs.values())


def _score_redirect(value: str) -> int:
    """Score a string as an OAuth2 redirect uri."""
    match = REDIRECT_RE.match(value)
    if not match or match.group(1).lower() in COMMON_SCHEMES:
        return 0
    score = 5
    if "." in match.group(1):
        score += 3  # reverse-DNS scheme, as recommended for native apps
    if re.search(r"(code|grant|auth|redirect|callback|oauth)", value, re.IGNORECASE):
        score += 4
    return score


def _score_client_id(value: str) -> int:
    """Score a string as an OAuth2 client id."""
    if not CLIENT_ID_RE.match(value) or not 4 <= len(value) <= 40:
        return 0
    if value.count(".") > 1:  # a package or class name
        return 0
    hits = sum(hint in value for hint in CLIENT_ID_HINTS)
    return 0 if not hits else 3 + 2 * hits + (2 if "-" in value else 0)


def _score_secret(value: str) -> int:
    """Score a string as an OAuth2 client secret.

    The competition here is the app's own symbol names, so the signal that
    matters is looking *unlike* an identifier: camel case runs out of upper
    case letters, a random secret does not.
    """
    if not SECRET_RE.match(value):
        return 0
    has_upper = any(c.isupper() for c in value)
    has_lower = any(c.islower() for c in value)
    if not (has_upper and has_lower):
        return 0
    upper_runs = len(UPPER_RUN_RE.findall(value))
    if not upper_runs:
        return 0  # plain camel case, i.e. a method or class name
    score = 2 + 3 * min(upper_runs, 3)
    if any(c.isdigit() for c in value):
        score += 2
    if len(set(value)) >= len(value) * 0.6:
        score += 2
    if 24 <= len(value) <= 48:
        score += 2
    return score


def rank(strings: list[str]) -> dict[str, list[Candidate]]:
    """Rank the collected strings as candidates for each credential."""
    scorers = {
        "redirect_uri": _score_redirect,
        "client_id": _score_client_id,
        "client_secret": _score_secret,
    }
    results: dict[str, list[Candidate]] = {}
    for field, scorer in scorers.items():
        seen: dict[str, Candidate] = {}
        for value in strings:
            if value in seen:
                continue
            score = scorer(value)
            if score:
                seen[value] = Candidate(value, score, field)
        results[field] = sorted(seen.values(), key=lambda c: -c.score)
    return results


def _preferred_pair(pairs: list[ClientPair], wanted: str | None) -> ClientPair | None:
    """Pick the client pair to report, preferring an explicitly requested id."""
    if not pairs:
        return None
    if wanted:
        return next((p for p in pairs if p.client_id == wanted), None)
    # Without a preference, favour the id that names a platform over a generic
    # one, which in practice is the client the mobile app itself logs in with.
    ranked = sorted(pairs, key=lambda p: -_score_client_id(p.client_id))
    return ranked[0]


def main() -> int:
    """Run the extraction."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("apk", type=Path, help="path to the Cookidoo APK")
    parser.add_argument(
        "--env",
        action="store_true",
        help="print the best candidates as .env assignments",
    )
    parser.add_argument(
        "--client-id",
        metavar="ID",
        help="use the client with this exact id when the APK ships several",
    )
    parser.add_argument(
        "--grep",
        metavar="PATTERN",
        help="instead of ranking, print every extracted string matching PATTERN",
    )
    parser.add_argument(
        "--top", type=int, default=5, help="candidates to show per field (default: 5)"
    )
    args = parser.parse_args()

    if not args.apk.is_file():
        print(f"No such file: {args.apk}", file=sys.stderr)
        return 1

    print(f"Reading {args.apk} ...", file=sys.stderr)
    strings, explicit = collect_strings(args.apk)
    print(f"Collected {len(strings)} strings.", file=sys.stderr)

    if args.grep:
        pattern = re.compile(args.grep, re.IGNORECASE)
        for value in sorted({s for s in strings if pattern.search(s)}):
            print(value)
        return 0

    pairs = basic_auth_pairs(strings)
    preferred = _preferred_pair(pairs, args.client_id)
    ranked = rank(strings)

    best = {field: explicit.get(field) for field in CONFIG_KEYS}
    if preferred:
        best["client_id"] = best["client_id"] or preferred.client_id
        best["client_secret"] = best["client_secret"] or preferred.client_secret
    for field, candidates in ranked.items():
        if not best[field] and candidates:
            best[field] = candidates[0].value

    if args.env:
        for field, value in best.items():
            print(f"{field.upper()}={value or ''}")
        if not all(best.values()):
            print("Some fields had no candidate, see the full report.", file=sys.stderr)
        return 0

    if pairs:
        print("\nclient credentials (decoded from a Basic auth header):")
        for pair in pairs:
            mark = " <-- selected" if pair == preferred else ""
            print(f"  {pair.client_id}:{pair.client_secret}{mark}")
        print(
            "  An app ships one client per environment it can reach. Pick the "
            "one whose id matches the flow you want, --client-id filters."
        )
        if preferred and sum(p.client_id == preferred.client_id for p in pairs) > 1:
            print(
                f"  Note: several secrets exist for '{preferred.client_id}' "
                "(one per environment). If the token endpoint answers "
                "invalid_client, try the other one."
            )

    for field in CONFIG_KEYS:
        print(f"\n{field}:")
        if explicit.get(field):
            print(f"  {explicit[field]}   (read from a config asset)")
        for candidate in ranked[field][: args.top]:
            print(f"  {candidate.value}   (score {candidate.score})")
        if not explicit.get(field) and not ranked[field]:
            print("  no candidate, try --grep")
    print(
        "\nVerify before use, and keep the values out of version control. "
        "See docs/oauth-client.md.",
        file=sys.stderr,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
