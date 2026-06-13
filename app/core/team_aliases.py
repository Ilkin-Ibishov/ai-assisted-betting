import json
import unicodedata
from dataclasses import dataclass
from pathlib import Path

DEFAULT_ALIAS_PATH = Path(__file__).resolve().parents[2] / "data" / "team_aliases.json"


@dataclass(frozen=True)
class TeamAlias:
    source: str
    alias: str
    canonical: str
    league: str | None = None
    confidence: str = "manual"


class TeamAliasResolver:
    def __init__(self, aliases: list[TeamAlias] | None = None) -> None:
        self._aliases_by_key: dict[tuple[str, str | None], set[str]] = {}
        for alias in aliases or []:
            key = (canonical_team_key(alias.alias), alias.league)
            self._aliases_by_key.setdefault(key, set()).add(canonical_team_key(alias.canonical))

    @classmethod
    def from_json_file(cls, path: Path = DEFAULT_ALIAS_PATH) -> "TeamAliasResolver":
        if not path.exists():
            return cls()
        payload = json.loads(path.read_text(encoding="utf-8"))
        aliases = [
            TeamAlias(
                source=str(item["source"]),
                alias=str(item["alias"]),
                canonical=str(item["canonical"]),
                league=str(item["league"]) if item.get("league") else None,
                confidence=str(item.get("confidence") or "manual"),
            )
            for item in payload
        ]
        return cls(aliases)

    def canonical_keys(self, team: str, *, league: str | None = None) -> set[str]:
        direct_key = canonical_team_key(team)
        keys = {direct_key}
        alias_keys = self._aliases_by_key.get((direct_key, league), set())
        alias_keys |= self._aliases_by_key.get((direct_key, None), set())
        if len(alias_keys) == 1:
            keys |= alias_keys
        return keys


def canonical_team_key(value: str) -> str:
    transliterated = (
        value.replace("\u0259", "e")
        .replace("\u018f", "E")
        .replace("\u0131", "i")
        .replace("\u0130", "I")
        .replace("\u00f6", "o")
        .replace("\u00d6", "O")
        .replace("\u00fc", "u")
        .replace("\u00dc", "U")
        .replace("\u011f", "g")
        .replace("\u011e", "G")
        .replace("\u015f", "s")
        .replace("\u015e", "S")
        .replace("\u00e7", "c")
        .replace("\u00c7", "C")
    )
    normalized = unicodedata.normalize("NFKD", transliterated)
    ascii_text = normalized.encode("ascii", "ignore").decode("ascii").lower()
    tokens = (
        "".join(character if character.isalnum() else " " for character in ascii_text).split()
    )
    compacted: list[str] = []
    index = 0
    while index < len(tokens):
        if len(tokens[index]) == 1:
            acronym = tokens[index]
            index += 1
            while index < len(tokens) and len(tokens[index]) == 1:
                acronym += tokens[index]
                index += 1
            compacted.append(acronym)
            continue
        compacted.append(tokens[index])
        index += 1
    return " ".join(compacted)
