import json

import pytest

from faceless import marketing


def test_net_per_sale_matches_the_fee_schedule():
    assert marketing.net_per_sale(17) == 14.01
    assert marketing.net_per_sale(14) == pytest.approx(11.39, abs=0.01)
    assert marketing.net_per_sale(24) == pytest.approx(20.10, abs=0.01)


def facts(**kw):
    base = {"planner_live": False, "newsletter_form": False, "coverage": {48: 0, 168: 0}}
    return {**base, **kw}


def test_experiments_are_blocked_until_their_inputs_exist():
    f = facts()
    assert "not live" in marketing.blockers("X1", f)
    assert marketing.blockers("X1", facts(planner_live=True)) is None
    assert "form action" in marketing.blockers("X3", f) and marketing.blockers("X3", facts(newsletter_form=True)) is None
    assert marketing.blockers("X4", facts(coverage={48: 25, 168: 0})) is None
    assert "owner" in marketing.blockers("X7", f)


def test_register_moves_and_rejects_bad_status(tmp_path, monkeypatch):
    reg = tmp_path / "experiments.json"
    reg.write_text(json.dumps({"experiments": [{"id": "X1", "status": "planned", "hypothesis": "h", "autonomy": "auto"}]}), encoding="utf-8")
    monkeypatch.setattr(marketing, "REGISTER", reg)
    assert marketing.set_experiment("X1", "running")["started"]
    assert marketing.set_experiment("X1", "won", "3 of 200")["result"] == "3 of 200"
    with pytest.raises(ValueError):
        marketing.set_experiment("X1", "maybe")
    with pytest.raises(KeyError):
        marketing.set_experiment("X99", "won")


def test_owner_queue_shows_three_open_items_and_closes_them(tmp_path, monkeypatch):
    q = tmp_path / "q.json"
    q.write_text(json.dumps({"items": [{"id": f"U0{i}", "ask": f"ask {i}", "status": "open"} for i in range(1, 6)]}), encoding="utf-8")
    monkeypatch.setattr(marketing, "QUEUE", q)
    assert [i["id"] for i in marketing.owner_queue()] == ["U01", "U02", "U03"]
    marketing.mark_done("U01")
    assert [i["id"] for i in marketing.owner_queue()] == ["U02", "U03", "U04"]
    with pytest.raises(KeyError):
        marketing.mark_done("U77")


def test_sales_summary_nets_fees_and_ignores_refunds(tmp_path, monkeypatch):
    p = tmp_path / "sales.jsonl"
    p.write_text("\n".join(json.dumps(r) for r in [{"id": 1, "usd": 17.0}, {"id": 2, "usd": 17.0, "refunded": True}, {"id": 3, "usd": 17.0}]) + "\n", encoding="utf-8")
    monkeypatch.setattr(marketing, "SALES", p)
    s = marketing.sales_summary()
    assert s["sales"] == 2 and s["gross"] == 34.0 and s["net_estimate"] == 28.02 and s["to_gate"] == 71.98


def test_brief_reads_without_writing_anything_public(monkeypatch):
    text = marketing.brief()
    assert text.startswith("# Marketing brief") and "## Guards" in text and "## Owner queue" in text
