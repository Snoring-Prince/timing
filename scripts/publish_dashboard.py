"""VIX를 숨긴 대시보드용 파일. 수집 원본과 계산은 그대로 보존한다.

각 수집 workflow에서 해당 파일만 만든다. 인자 없이 실행하면 셋 모두 생성.
부분 수집 실패 때도 원본의 보존된 값·시각을 그대로 전달한다.
"""
import argparse
import copy
import json
from pathlib import Path

DATA = Path(__file__).resolve().parent.parent / "data"
FILES = ("market.json", "market-long.json", "backtest.json")


def project(name, source):
    result = copy.deepcopy(source)
    if name == "market.json":
        result.pop("vix", None)
    elif name == "market-long.json":
        result["series"].pop("vix", None)
    elif name == "backtest.json":
        result["axes"] = [a for a in result["axes"] if a["key"] != "vix"]
        for index in result["indices"].values():
            index["curve"].pop("vix", None)
    else:
        raise ValueError(f"지원하지 않는 파일: {name}")
    return result


def publish(name, data=DATA):
    source = json.loads((data / name).read_text(encoding="utf-8"))
    payload = json.dumps(project(name, source), ensure_ascii=False, separators=(",", ":"))
    target = data / "dashboard" / name
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_suffix(".tmp")
    temporary.write_text(payload, encoding="utf-8")
    temporary.replace(target)
    print(f"{target}: {len(payload.encode('utf-8')):,} bytes")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("files", nargs="*")
    args = parser.parse_args()
    if set(args.files) - set(FILES):
        parser.error("지원 파일: " + ", ".join(FILES))
    for name in args.files or FILES:
        publish(name)
