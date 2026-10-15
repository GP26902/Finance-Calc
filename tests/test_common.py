from modules.common import esc, fmt


def test_esc_escapes_every_dollar_sign():
    assert esc("saves $1,000 vs $2,000") == r"saves \$1,000 vs \$2,000"


def test_esc_is_idempotent_and_leaves_plain_text_alone():
    once = esc("EUAC $45,134 vs $54,840")
    assert esc(once) == once
    assert esc("no currency here, only ₹ and £") == "no currency here, only ₹ and £"


def test_fmt_itself_stays_plain_so_tables_and_metrics_are_not_escaped():
    assert fmt("$", -1234.5) == "-$1,234.50"
