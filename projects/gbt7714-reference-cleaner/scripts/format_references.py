#!/usr/bin/env python3
"""Offline, deterministic GB/T 7714 common-type formatting and conservative dedup.

The caller/model extracts bibliographic meaning into JSON first. This module never
queries a service, invents metadata, or automatically removes fuzzy matches.
Python 3.10+; standard library only.
"""
from __future__ import annotations

import argparse
import copy
import datetime as dt
import difflib
import json
import re
import sys
import unicodedata
from pathlib import Path
from urllib.parse import unquote, urlsplit


TYPE_ALIASES = {
    "j": "J", "journal": "J", "article": "J",
    "c": "C", "conference": "C", "inproceedings": "C",
    "m": "M", "book": "M", "monograph": "M",
    "d": "D", "thesis": "D", "dissertation": "D",
    "eb/ol": "EB/OL", "ebol": "EB/OL", "web": "EB/OL",
}
TEXT_FIELDS = (
    "title", "year", "container", "volume", "issue", "pages", "place",
    "publisher", "edition", "doi", "url", "access_date", "date",
)
SUPPORTED_TYPES = {"J", "C", "M", "D", "EB/OL"}
TRUNCATION_MARKERS = {"等", "etal", "andothers"}


def clean(value: object) -> str:
    """NFKC and whitespace only: no content paraphrasing or missing-field guesses."""
    if value is None:
        return ""
    if not isinstance(value, (str, int, float)) or isinstance(value, bool):
        return ""
    return re.sub(r"\s+", " ", unicodedata.normalize("NFKC", str(value))).strip()


def key(value: object) -> str:
    return "".join(c for c in clean(value).casefold() if c.isalnum())


def title_key(value: object) -> str:
    # Internal punctuation can carry meaning (A+B versus AB, re-vision versus
    # revision). Ignore spacing/case, but do not erase mathematical punctuation.
    return re.sub(r"\s+", "", clean(value).casefold())


def normalize_doi(value: str) -> str:
    value = unquote(clean(value))
    value = re.sub(r"^(?:https?://(?:dx\.)?doi\.org/|doi\s*:\s*)", "", value,
                   flags=re.IGNORECASE).strip().rstrip(".,;。；")
    while value.endswith(")") and value.count(")") > value.count("("):
        value = value[:-1]
    return value.casefold()


def valid_doi(value: str) -> bool:
    return bool(re.fullmatch(r"10\.\d{4,9}/[^\s]+", value, flags=re.IGNORECASE))


def valid_date(value: str) -> bool:
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
        return False
    try:
        dt.date.fromisoformat(value)
        return True
    except ValueError:
        return False


def valid_url(value: str) -> bool:
    try:
        parts = urlsplit(value)
        return parts.scheme in {"http", "https"} and bool(parts.netloc) and not re.search(r"\s", value)
    except ValueError:
        return False


def initials(given: str) -> str:
    """Initials for an explicitly structured Western given-name field only."""
    tokens = re.findall(r"[^\W\d_]+", given, re.UNICODE)
    return " ".join(t[0].upper() for t in tokens if t)


def author_text(author: str | dict, author_case: str = "preserve") -> str:
    if isinstance(author, dict):
        if author.get("literal"):
            return author["literal"]
        family = author.get("family", "")
        if author_case == "upper":
            family = family.upper()
        return " ".join(p for p in (family, initials(author.get("given", ""))) if p)
    if author_case == "upper" and not re.search(r"[\u3400-\u9fff]", author):
        return author.upper()
    return author


def author_keys(record: dict) -> list[str]:
    return [key(author_text(a)) for a in record["authors"]]


def add_issue(record: dict, code: str, field: str, message: str) -> None:
    issue = {"code": code, "field": field, "message": message}
    if issue not in record["issues"]:
        record["issues"].append(issue)


def normalize_record(raw: object, index: int) -> dict:
    record = {"id": f"r{index:02d}", "type": "", "authors": [],
              "authors_truncated": False, "language": "", "issues": []}
    record["raw_input"] = copy.deepcopy(raw)
    record.update({f: "" for f in TEXT_FIELDS})
    record["source_indices"] = [index]
    if not isinstance(raw, dict):
        record["source_ids"] = [record["id"]]
        record["source_records"] = [{"source_index": index, "source_id": record["id"],
                                      "raw_input": copy.deepcopy(raw)}]
        add_issue(record, "invalid_record", "record", "条目必须是 JSON 对象，原值保留待人工处理")
        return record
    record["id"] = clean(raw.get("id")) or record["id"]
    record["source_ids"] = [record["id"]]
    record["source_records"] = [{"source_index": index, "source_id": record["id"],
                                  "raw_input": copy.deepcopy(raw)}]
    record["type"] = TYPE_ALIASES.get(clean(raw.get("type")).casefold(), clean(raw.get("type")))
    for field in TEXT_FIELDS:
        value = raw.get(field)
        record[field] = clean(value)
        if value is not None and value != "" and not record[field]:
            add_issue(record, "invalid_field_type", field, "字段应为字符串或数字，原值未作为有效著录信息")
    record["title"] = record["title"].rstrip(" .。")
    record["container"] = record["container"].rstrip(" .。")
    record["issue"] = record["issue"].strip("()")
    record["pages"] = re.sub(r"^(?:pp?\.?\s*)", "", record["pages"], flags=re.IGNORECASE)
    record["pages"] = re.sub(r"\s*[-–—−]+\s*", "-", record["pages"])
    record["doi"] = normalize_doi(record["doi"])
    if record["doi"] and not valid_doi(record["doi"]):
        add_issue(record, "invalid_doi", "doi", "DOI 形式无效，不用于自动去重")
    record["edition"] = record["edition"].rstrip(" .。")
    if record["edition"].isdigit():
        record["edition"] += "版"
    if record["year"] and not re.fullmatch(r"\d{4}", record["year"]):
        add_issue(record, "invalid_year", "year", "年份须为四位数字；不从其他字段猜测年份")
    for field in ("date", "access_date"):
        if record[field] and not valid_date(record[field]):
            add_issue(record, "invalid_date", field, "日期须为真实的 YYYY-MM-DD 日期")
    if record["url"] and not valid_url(record["url"]):
        add_issue(record, "invalid_url", "url", "URL 须为完整的 http 或 https 地址")
    values = raw.get("authors", [])
    if not isinstance(values, list):
        add_issue(record, "invalid_authors", "authors", "authors 须为列表；姓名语义拆分应由智能体完成")
        values = []
    record["authors_truncated"] = raw.get("authors_truncated") is True
    for a in values:
        if isinstance(a, str):
            a = clean(a).strip(" ,;。")
            if key(a) in TRUNCATION_MARKERS:
                record["authors_truncated"] = True
            elif a:
                record["authors"].append(a)
        elif isinstance(a, dict):
            if clean(a.get("literal")):
                record["authors"].append({"literal": clean(a["literal"])})
            elif clean(a.get("family")):
                record["authors"].append({"family": clean(a["family"]), "given": clean(a.get("given"))})
            else:
                add_issue(record, "invalid_author", "authors", "作者对象须有 literal 或 family")
        else:
            add_issue(record, "invalid_author", "authors", "作者须为规范短名字符串或姓名对象")
    lang = clean(raw.get("language")).casefold()
    if lang in {"zh", "zh-cn", "cn", "chinese"}:
        record["language"] = "zh"
    elif lang in {"en", "english"}:
        record["language"] = "en"
    elif not lang:
        names = " ".join(author_text(a) for a in record["authors"])
        record["language"] = "zh" if re.search(r"[\u3400-\u9fff]", names) else "en"
    else:
        record["language"] = lang
        add_issue(record, "invalid_language", "language", "language 仅支持 zh 或 en，需由智能体确认")
    if record["type"] not in SUPPORTED_TYPES:
        add_issue(record, "unsupported_type", "type", "类型须为 J、C、M、D 或 EB/OL，不自动猜测")
    if record["authors_truncated"]:
        add_issue(record, "truncated_authors", "authors", "输入作者已截断，保留等或 et al 标记，不恢复未知作者")
    return record


def authors_compatible(left: dict, right: dict) -> bool:
    a, b = author_keys(left), author_keys(right)
    if not a or not b or a == b:
        return True
    if left["authors_truncated"] and a == b[:len(a)]:
        return True
    if right["authors_truncated"] and b == a[:len(b)]:
        return True
    return False


def conflicts(left: dict, right: dict) -> list[str]:
    found = []
    for field in ("type", "title", "year", "language", "container", "volume", "issue",
                  "pages", "place", "publisher", "edition", "doi", "date", "url"):
        a, b = left.get(field, ""), right.get(field, "")
        if field == "title":
            equal = title_key(a) == title_key(b)
        elif field in {"doi", "year", "volume", "issue", "pages", "date", "url"}:
            # In an identifier/range, punctuation is significant. In particular,
            # DOI foo-a and fooa must never collapse to the same identifier.
            equal = a == b
        else:
            equal = key(a) == key(b)
        if a and b and not equal:
            found.append(field)
    # The absence of an edition does not prove equality with a specified revision.
    if left["type"] == right["type"] == "M" and bool(left["edition"]) != bool(right["edition"]):
        found.append("edition")
    if not authors_compatible(left, right):
        found.append("authors")
    return found


def evidence(left: dict, right: dict) -> str:
    doi = left["doi"]
    if valid_doi(doi) and doi == right["doi"]:
        return "same_doi"
    a, b = author_keys(left), author_keys(right)
    if (left["title"] and left["year"] and a and b and left["type"] in SUPPORTED_TYPES
            and left["type"] == right["type"] and title_key(left["title"]) == title_key(right["title"])
            and left["year"] == right["year"] and a[0] == b[0]):
        return "same_title_first_author_year_type"
    return ""


def merge_into(left: dict, right: dict) -> list[str]:
    enriched = []
    for field in (*TEXT_FIELDS, "type", "language"):
        if not left.get(field) and right.get(field):
            left[field] = right[field]
            enriched.append(field)
    if not left["authors"] and right["authors"]:
        left["authors"] = copy.deepcopy(right["authors"])
        left["authors_truncated"] = right["authors_truncated"]
        enriched.append("authors")
    elif (left["authors_truncated"] and not right["authors_truncated"]
          and author_keys(left) == author_keys(right)[:len(left["authors"])]):
        left["authors"] = copy.deepcopy(right["authors"])
        left["authors_truncated"] = False
        enriched.extend(["authors", "authors_truncated"])
    left["source_ids"].extend(right["source_ids"])
    left["source_indices"].extend(right["source_indices"])
    left["source_records"].extend(copy.deepcopy(right["source_records"]))
    for item in right["issues"]:
        if item not in left["issues"]:
            left["issues"].append(item)
    return enriched


def deduplicate(records: list[dict]) -> tuple[list[dict], list[dict]]:
    unique, duplicates = [], []
    for rec in records:
        for retained in unique:
            reason = evidence(retained, rec)
            if reason and not conflicts(retained, rec):
                changes = merge_into(retained, rec)
                duplicates.append({"kept_source_id": retained["id"],
                                   "duplicate_source_id": rec["id"],
                                   "duplicate_source_index": rec["source_indices"][0],
                                   "reason": reason, "enriched_fields": changes})
                break
        else:
            unique.append(copy.deepcopy(rec))
    return unique, duplicates


def review_candidates(records: list[dict]) -> list[dict]:
    candidates = []
    for i, a in enumerate(records):
        for j in range(i + 1, len(records)):
            b = records[j]
            ka, kb = title_key(a["title"]), title_key(b["title"])
            reason, ratio = "", None
            if evidence(a, b):
                reason = "metadata_conflict"
            elif ka and ka == kb:
                reason = "same_title_needs_review"
            elif ka and kb and min(len(ka), len(kb)) >= 8:
                aa, ab = author_keys(a), author_keys(b)
                if (aa and ab and aa[0] == ab[0]
                        and (not a["year"] or not b["year"] or a["year"] == b["year"])):
                    ratio = difflib.SequenceMatcher(None, ka, kb).ratio()
                    if ratio >= 0.88:
                        reason = "near_title_only"
            if reason:
                item = {"left_unique_index": i + 1, "right_unique_index": j + 1,
                        "left_source_ids": a["source_ids"], "right_source_ids": b["source_ids"],
                        "reason": reason, "conflict_fields": conflicts(a, b),
                        "action": "retained_both_for_review"}
                if ratio is not None:
                    item["title_similarity"] = round(ratio, 4)
                candidates.append(item)
    return candidates


def required_problems(record: dict) -> list[str]:
    # Deliberately conservative product quality gates, not a claim that every
    # listed field is mandatory under every clause of GB/T 7714.
    needed = ["type", "authors", "title"]
    needed += {
        "J": ["year", "container"],
        "C": ["year", "container", "publisher", "pages"],
        "M": ["year", "place", "publisher"],
        "D": ["year", "place", "publisher"],
        "EB/OL": ["url", "date", "access_date"],
    }.get(record["type"], [])
    problems = []
    for field in needed:
        if not record.get(field):
            problems.append(field)
            add_issue(record, "missing_field", field, "未达到本技能成稿质量门槛，保留草稿待补充")
    if record["type"] not in SUPPORTED_TYPES and "type" not in problems:
        problems.append("type")
    for issue in record["issues"]:
        if issue["code"] in {"invalid_year", "invalid_date", "invalid_url", "invalid_language", "invalid_author"}:
            if issue["field"] not in problems:
                problems.append(issue["field"])
    if record["type"] == "J":
        for field in ("volume", "issue", "pages"):
            if not record[field]:
                add_issue(record, "incomplete_optional_field", field, "期刊卷期页信息未提供，按已知字段输出并提醒核验")
    if record["type"] == "C" and not record["place"]:
        add_issue(record, "incomplete_optional_field", "place", "会议出版地未提供，按课程示例省略并提醒核验")
    return problems


def format_authors(record: dict, author_case: str) -> str:
    names = [author_text(a, author_case) for a in record["authors"][:3]]
    if len(record["authors"]) > 3 or record["authors_truncated"]:
        names.append("等" if record["language"] == "zh" else "et al")
    return ", ".join(names)


def format_record(record: dict, number: int, author_case: str = "preserve", include_doi: bool = False) -> str:
    head = f"[{number}] {format_authors(record, author_case)}. {record['title']}[{record['type']}]"
    kind = record["type"]
    if kind == "J":
        body = f". {record['container']}, {record['year']}"
        if record["volume"]:
            body += f", {record['volume']}"
        if record["issue"]:
            body += f"({record['issue']})"
        if record["pages"]:
            body += f": {record['pages']}"
    elif kind == "C":
        publication = f"{record['place']}: " if record["place"] else ""
        body = f"//{record['container']}. {publication}{record['publisher']}, {record['year']}: {record['pages']}"
    elif kind in {"M", "D"}:
        edition = f"{record['edition']}. " if record["edition"] else ""
        body = f". {edition}{record['place']}: {record['publisher']}, {record['year']}"
        if record["pages"]:
            body += f": {record['pages']}"
    elif kind == "EB/OL":
        body = f". ({record['date']})[{record['access_date']}]. {record['url']}"
    else:
        raise ValueError("unsupported type must remain a draft")
    line = head + body.rstrip(" .") + "."
    if include_doi and valid_doi(record["doi"]):
        line += f" DOI: {record['doi']}."
    return line


def process_records(raw_records: list, author_case: str = "preserve", include_doi: bool = False) -> dict:
    """Public pure-data entry point used by CLI and independent tests."""
    normalized = [normalize_record(raw, i) for i, raw in enumerate(raw_records, 1)]
    unique, duplicates = deduplicate(normalized)
    candidates = review_candidates(unique)
    references, drafts, warnings, mappings = [], [], [], []
    for index, record in enumerate(unique, 1):
        problems = required_problems(record)
        output_number = None
        if problems:
            status = "draft"
            drafts.append({"unique_index": index, "source_ids": record["source_ids"],
                           "title": record["title"], "problems": problems, "record": record})
        else:
            status = "formatted"
            output_number = len(references) + 1
            references.append(format_record(record, output_number, author_case, include_doi))
        record["status"] = status
        record["output_number"] = output_number
        for issue in record["issues"]:
            warnings.append({"unique_index": index, "source_ids": record["source_ids"], **issue})
        for source_index, source_id in zip(record["source_indices"], record["source_ids"]):
            mappings.append({"source_index": source_index, "source_id": source_id,
                             "unique_index": index, "output_number": output_number, "status": status})
    summary = {"input_count": len(raw_records), "unique_count": len(unique),
               "duplicate_count": len(duplicates), "formatted_count": len(references),
               "draft_count": len(drafts), "review_candidate_count": len(candidates)}
    audit = {"schema_version": "1.0", "profile": "gbt7714-common-types", "summary": summary,
             "duplicates": duplicates, "warnings": warnings, "review_candidates": candidates,
             "source_to_output": sorted(mappings, key=lambda m: m["source_index"])}
    return {"references": references, "drafts": drafts,
            "normalized": {"schema_version": "1.0", "records": unique}, "audit": audit}


def load_records(path: Path) -> list:
    with path.open("r", encoding="utf-8-sig") as stream:
        data = json.load(stream)
    if isinstance(data, dict) and isinstance(data.get("records"), list):
        return data["records"]
    if isinstance(data, list):
        return data
    raise ValueError('JSON 顶层须为列表或 {"records": [...]}')


def write_json(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, type=Path, help="UTF-8 JSON input")
    parser.add_argument("--outdir", required=True, type=Path, help="output directory")
    parser.add_argument("--author-case", choices=("preserve", "upper"), default="preserve")
    parser.add_argument("--include-doi", action="store_true", help="append valid DOI as an optional item")
    args = parser.parse_args(argv)
    filenames = ("references.txt", "drafts.txt", "normalized.json", "audit.json")
    if any(args.input.resolve() == (args.outdir / name).resolve() for name in filenames):
        print("输入文件不能与输出文件同路径，以免覆盖原始输入", file=sys.stderr)
        return 2
    try:
        records = load_records(args.input)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(json.dumps({"error": "input_error", "message": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 2
    result = process_records(records, args.author_case, args.include_doi)
    try:
        args.outdir.mkdir(parents=True, exist_ok=True)
        (args.outdir / "references.txt").write_text("\n".join(result["references"]) + ("\n" if result["references"] else ""), encoding="utf-8")
        draft_text = []
        for draft in result["drafts"]:
            draft_text.append(f"来源 {', '.join(draft['source_ids'])} | 待补充或核验: {', '.join(draft['problems'])}\n"
                              f"题名: {draft['title'] or '[未提供]'}\n"
                              + json.dumps(draft["record"], ensure_ascii=False, indent=2))
        (args.outdir / "drafts.txt").write_text("\n\n".join(draft_text) + ("\n" if draft_text else ""), encoding="utf-8")
        write_json(args.outdir / "normalized.json", result["normalized"])
        write_json(args.outdir / "audit.json", result["audit"])
    except OSError as exc:
        print(json.dumps({"error": "output_error", "message": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 2
    print(json.dumps(result["audit"]["summary"], ensure_ascii=False))
    wholly_invalid = bool(records) and not any(r["type"] in SUPPORTED_TYPES for r in result["normalized"]["records"])
    return 2 if wholly_invalid else 0


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    raise SystemExit(main())
