#!/usr/bin/env python3
"""Monitor the BAC results page and try candidate lookups automatically."""

from __future__ import annotations

import argparse
import hashlib
import re
import sys
import time
import unicodedata
from dataclasses import dataclass
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from urllib import error, parse, request


DEFAULT_URL = "https://itdeco.ci/examens/resultat/bac/redis/"
DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/126.0.0.0 Safari/537.36"
)
FALLBACK_FIELD_NAMES = [
    "matricule",
    "matric",
    "numero",
    "num_table",
    "code",
    "search",
    "q",
]
POSITIVE_KEYWORDS = [
    "admis",
    "ajourne",
    "ajournee",
    "mention",
    "moyenne",
    "decision",
    "nom",
    "prenoms",
    "etablissement",
    "serie",
]
NEGATIVE_KEYWORDS = [
    "aucun resultat",
    "aucun enregistrement",
    "introuvable",
    "non trouve",
    "invalide",
    "erreur",
]


@dataclass
class CheckResult:
    status: int
    final_url: str
    body_hash: str
    body_preview: str
    body_text: str


@dataclass
class FormSpec:
    method: str
    action_url: str
    hidden_fields: dict[str, str]
    candidate_fields: list[str]


class FormCollector(HTMLParser):
    def __init__(self, base_url: str) -> None:
        super().__init__()
        self.base_url = base_url
        self.forms: list[FormSpec] = []
        self._current_method = "get"
        self._current_action_url = base_url
        self._current_hidden_fields: dict[str, str] | None = None
        self._current_candidate_fields: list[str] | None = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attr_map = {key.lower(): value or "" for key, value in attrs}

        if tag.lower() == "form":
            action = attr_map.get("action") or self.base_url
            method = (attr_map.get("method") or "get").lower()
            self._current_method = "post" if method == "post" else "get"
            self._current_action_url = parse.urljoin(self.base_url, action)
            self._current_hidden_fields = {}
            self._current_candidate_fields = []
            return

        if tag.lower() != "input" or self._current_hidden_fields is None:
            return

        field_name = attr_map.get("name", "").strip()
        field_type = (attr_map.get("type") or "text").lower()

        if not field_name:
            return

        if field_type == "hidden":
            self._current_hidden_fields[field_name] = attr_map.get("value", "")
            return

        if field_type in {"text", "search", "number", "tel"}:
            self._current_candidate_fields.append(field_name)

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() != "form" or self._current_hidden_fields is None:
            return

        candidate_fields = unique_list(self._current_candidate_fields or [])
        self.forms.append(
            FormSpec(
                method=self._current_method,
                action_url=self._current_action_url,
                hidden_fields=dict(self._current_hidden_fields),
                candidate_fields=candidate_fields,
            )
        )
        self._current_hidden_fields = None
        self._current_candidate_fields = None


def unique_list(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        result.append(value)
    return result


def normalize_text(text: str) -> str:
    return unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode().lower()


def timestamp() -> str:
    return datetime.now(timezone.utc).astimezone().strftime("%Y-%m-%d %H:%M:%S %Z")


def fetch(url: str, timeout: float, data: bytes | None = None) -> CheckResult:
    last_exception: Exception | None = None

    for _ in range(3):
        req = request.Request(url, headers={"User-Agent": DEFAULT_USER_AGENT}, data=data)

        try:
            with request.urlopen(req, timeout=timeout) as response:
                body = response.read()
                return build_result(response.status, response.geturl(), body)
        except error.HTTPError as exc:
            body = exc.read()
            return build_result(exc.code, exc.geturl(), body)
        except Exception as exc:  # pragma: no cover - transient network retries
            last_exception = exc
            time.sleep(1)

    assert last_exception is not None
    raise last_exception


def build_result(status: int, final_url: str, body: bytes) -> CheckResult:
    body_text = body.decode("utf-8", "replace")
    return CheckResult(
        status=status,
        final_url=final_url,
        body_hash=hashlib.sha256(body).hexdigest()[:16],
        body_preview=body_text[:200].replace("\n", " "),
        body_text=body_text,
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Surveille une page de resultat et tente les matricules automatiquement."
    )
    parser.add_argument("--url", default=DEFAULT_URL, help="URL a verifier")
    parser.add_argument(
        "--matricule",
        action="append",
        default=[],
        help="Matricule a verifier. Reutiliser l'option pour plusieurs candidats.",
    )
    parser.add_argument(
        "--interval",
        type=float,
        default=60.0,
        help="Delai entre deux verifications, en secondes",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=20.0,
        help="Timeout HTTP par requete, en secondes",
    )
    parser.add_argument(
        "--max-checks",
        type=int,
        default=0,
        help="Nombre max de verifications avant arret; 0 = infini",
    )
    parser.add_argument(
        "--stop-on-status",
        type=int,
        nargs="+",
        default=[200],
        help="Codes HTTP qui signalent que la page est potentiellement prete",
    )
    parser.add_argument(
        "--stop-on-change",
        action="store_true",
        help="Tente aussi les matricules si le contenu ou l'URL changent",
    )
    parser.add_argument(
        "--output-dir",
        default="watch_outputs",
        help="Dossier des logs et des reponses capturees",
    )
    return parser.parse_args()


def log(message: str, log_path: Path) -> None:
    line = f"[{timestamp()}] {message}"
    print(line)
    sys.stdout.flush()
    with log_path.open("a", encoding="utf-8") as handle:
        handle.write(line + "\n")


def extract_forms(html_text: str, base_url: str) -> list[FormSpec]:
    parser = FormCollector(base_url)
    parser.feed(html_text)
    parser.close()
    forms = [form for form in parser.forms if form.candidate_fields or form.hidden_fields]
    return forms


def infer_field_names(forms: list[FormSpec], html_text: str) -> list[str]:
    field_names: list[str] = []

    for form in forms:
        field_names.extend(form.candidate_fields)

    for match in re.finditer(r'name=["\']([^"\']+)["\']', html_text, re.IGNORECASE):
        name = match.group(1).strip()
        lowered = normalize_text(name)
        if any(keyword in lowered for keyword in ("matric", "numero", "table", "code", "search")):
            field_names.append(name)

    field_names.extend(FALLBACK_FIELD_NAMES)
    return unique_list(field_names)


def build_form_candidates(page_result: CheckResult, base_url: str) -> list[FormSpec]:
    forms = extract_forms(page_result.body_text, page_result.final_url)
    inferred_names = infer_field_names(forms, page_result.body_text)

    if forms:
        prepared_forms: list[FormSpec] = []
        for form in forms:
            fields = unique_list(form.candidate_fields + inferred_names)
            prepared_forms.append(
                FormSpec(
                    method=form.method,
                    action_url=form.action_url,
                    hidden_fields=form.hidden_fields,
                    candidate_fields=fields,
                )
            )
        return prepared_forms

    return [
        FormSpec(
            method="get",
            action_url=page_result.final_url or base_url,
            hidden_fields={},
            candidate_fields=inferred_names,
        ),
        FormSpec(
            method="post",
            action_url=page_result.final_url or base_url,
            hidden_fields={},
            candidate_fields=inferred_names,
        ),
    ]


def save_snapshot(
    output_dir: Path,
    matricule: str,
    form: FormSpec,
    field_name: str,
    result: CheckResult,
) -> Path:
    safe_matricule = re.sub(r"[^0-9A-Za-z_-]", "_", matricule)
    safe_field = re.sub(r"[^0-9A-Za-z_-]", "_", field_name)
    safe_method = form.method.upper()
    filename = (
        f"{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        f"_{safe_matricule}_{safe_method}_{safe_field}_{result.status}.html"
    )
    path = output_dir / filename
    path.write_text(result.body_text, encoding="utf-8")
    return path


def extract_snippet(body_text: str, matricule: str) -> str:
    collapsed = re.sub(r"\s+", " ", body_text)
    normalized = normalize_text(collapsed)
    patterns = [matricule.lower()] + POSITIVE_KEYWORDS + NEGATIVE_KEYWORDS

    for pattern in patterns:
        index = normalized.find(normalize_text(pattern))
        if index == -1:
            continue
        start = max(index - 80, 0)
        end = min(index + 220, len(collapsed))
        return collapsed[start:end]

    return collapsed[:300]


def classify_lookup(result: CheckResult, base_page: CheckResult, matricule: str) -> str:
    normalized_body = normalize_text(result.body_text)
    matricule_lower = matricule.lower()

    if matricule_lower in normalized_body:
        if any(keyword in normalized_body for keyword in NEGATIVE_KEYWORDS):
            return "negative"
        if any(keyword in normalized_body for keyword in POSITIVE_KEYWORDS):
            return "found"
        if result.body_hash != base_page.body_hash:
            return "possible"

    if result.status == 200 and result.body_hash != base_page.body_hash:
        return "possible"

    return "none"


def submit_lookup(form: FormSpec, field_name: str, matricule: str, timeout: float) -> CheckResult:
    payload = dict(form.hidden_fields)
    payload[field_name] = matricule
    encoded = parse.urlencode(payload).encode()

    if form.method == "post":
        return fetch(form.action_url, timeout, data=encoded)

    target_url = form.action_url
    separator = "&" if parse.urlparse(target_url).query else "?"
    query = parse.urlencode(payload)
    return fetch(f"{target_url}{separator}{query}", timeout)


def try_lookup_for_page(
    page_result: CheckResult,
    base_url: str,
    pending_matricules: set[str],
    timeout: float,
    output_dir: Path,
    log_path: Path,
) -> set[str]:
    found_matricules: set[str] = set()
    forms = build_form_candidates(page_result, base_url)
    log(
        "Page ouverte: tentative automatique de recherche "
        f"avec {len(forms)} variante(s) de formulaire.",
        log_path,
    )

    for form in forms:
        for field_name in form.candidate_fields:
            for matricule in sorted(pending_matricules - found_matricules):
                try:
                    lookup_result = submit_lookup(form, field_name, matricule, timeout)
                except Exception as exc:
                    log(
                        f"Recherche {matricule} via {form.method.upper()} {field_name}: "
                        f"{type(exc).__name__}: {exc}",
                        log_path,
                    )
                    continue

                snapshot_path = save_snapshot(output_dir, matricule, form, field_name, lookup_result)
                state = classify_lookup(lookup_result, page_result, matricule)
                snippet = extract_snippet(lookup_result.body_text, matricule)
                log(
                    f"Recherche {matricule} via {form.method.upper()} {field_name}: "
                    f"status={lookup_result.status} hash={lookup_result.body_hash} "
                    f"etat={state} fichier={snapshot_path}",
                    log_path,
                )
                if snippet:
                    log(f"Apercu {matricule}: {snippet}", log_path)

                if state == "found":
                    found_matricules.add(matricule)

    return found_matricules


def main() -> int:
    args = parse_args()
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    log_path = output_dir / "bac_watch.log"
    stop_statuses = set(args.stop_on_status)
    last_result: CheckResult | None = None
    attempted_signatures: set[tuple[int, str, str]] = set()
    pending_matricules = set(args.matricule)
    checks = 0

    log(f"Surveillance: {args.url}", log_path)
    log(
        f"Intervalle={args.interval}s Timeout={args.timeout}s StopCodes={sorted(stop_statuses)} "
        f"StopOnChange={args.stop_on_change} Matricules={sorted(pending_matricules)}",
        log_path,
    )

    while True:
        checks += 1

        try:
            result = fetch(args.url, args.timeout)
        except Exception as exc:  # pragma: no cover - defensive logging
            log(f"Erreur reseau: {type(exc).__name__}: {exc}", log_path)
            if args.max_checks and checks >= args.max_checks:
                return 1
            time.sleep(args.interval)
            continue

        changed = (
            last_result is None
            or result.status != last_result.status
            or result.final_url != last_result.final_url
            or result.body_hash != last_result.body_hash
        )

        if changed:
            log(
                f"check={checks} status={result.status} final_url={result.final_url} "
                f"hash={result.body_hash}",
                log_path,
            )
            if result.body_preview:
                log(f"Apercu page: {result.body_preview}", log_path)

        page_signal = result.status in stop_statuses
        if args.stop_on_change and last_result is not None and changed:
            page_signal = True

        if page_signal and pending_matricules:
            signature = (result.status, result.final_url, result.body_hash)
            if signature not in attempted_signatures:
                attempted_signatures.add(signature)
                found = try_lookup_for_page(
                    page_result=result,
                    base_url=args.url,
                    pending_matricules=pending_matricules,
                    timeout=args.timeout,
                    output_dir=output_dir,
                    log_path=log_path,
                )
                pending_matricules -= found
                if found:
                    log(f"Matricules confirms: {sorted(found)}", log_path)
                if not pending_matricules:
                    log("Arret: resultats detectes pour tous les matricules.", log_path)
                    return 0
                log(
                    f"Surveillance continue: matricules encore en attente {sorted(pending_matricules)}",
                    log_path,
                )

        if not pending_matricules and page_signal:
            log(f"Arret: code HTTP attendu detecte ({result.status}).", log_path)
            return 0

        if args.max_checks and checks >= args.max_checks:
            log("Arret: nombre maximal de verifications atteint.", log_path)
            return 0

        last_result = result
        time.sleep(args.interval)


if __name__ == "__main__":
    raise SystemExit(main())
