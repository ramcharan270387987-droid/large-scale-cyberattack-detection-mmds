"""Exploratory pattern summaries for labeled historical traffic."""

from src.sql.traffic_analytics import finite


def benign_thresholds_sql(accuracy):
    return f"""SELECT percentile_approx(flow_pkts_s, 0.99D, {int(accuracy)}) AS packet_rate_p99,
 percentile_approx(total_packets, 0.99D, {int(accuracy)}) AS packet_count_p99,
 percentile_approx(total_bytes, 0.99D, {int(accuracy)}) AS byte_count_p99,
 percentile_approx(flow_duration, 0.1D, {int(accuracy)}) AS duration_p10,
 percentile_approx(flow_iat_mean, 0.99D, {int(accuracy)}) AS iat_p99
 FROM traffic WHERE population = 'benign'"""


def patterns_sql(thresholds):
    rules = [
        ("high_packet_rate", "flow_pkts_s IS NOT NULL", f"flow_pkts_s > {float(thresholds['packet_rate_p99'])!r}"),
        ("large_packet_count", "total_packets IS NOT NULL", f"total_packets > {float(thresholds['packet_count_p99'])!r}"),
        ("short_high_bytes", "flow_duration IS NOT NULL AND total_bytes IS NOT NULL",
         f"flow_duration <= {float(thresholds['duration_p10'])!r} AND total_bytes > {float(thresholds['byte_count_p99'])!r}"),
        ("high_mean_iat", "flow_iat_mean IS NOT NULL", f"flow_iat_mean > {float(thresholds['iat_p99'])!r}"),
    ]
    stats = [f"named_struct('pattern', '{name}', 'eligible', count_if({valid}), 'matches', count_if({valid} AND {condition}))"
             for name, valid, condition in rules]
    return (f"SELECT population, attack_family, m.* FROM (SELECT population, attack_family, explode(array({', '.join(stats)})) AS m "
            "FROM traffic GROUP BY population, attack_family) ORDER BY population, attack_family, m.pattern")


FLAGS_SQL = """SELECT population, attack_family, syn_flag_cnt > 0 AS syn, ack_flag_cnt > 0 AS ack,
 fin_flag_cnt > 0 AS fin, rst_flag_cnt > 0 AS rst, count(*) AS records
 FROM traffic WHERE protocol = 6
 GROUP BY population, attack_family, syn, ack, fin, rst
 ORDER BY population, attack_family, records DESC, syn, ack, fin, rst"""


def sensitivity_sql(layer):
    if layer not in {"raw_aligned", "clean"}:
        raise ValueError("Unknown sensitivity view")
    fields = ("flow_byts_s", "flow_pkts_s", "init_fwd_win_byts", "init_bwd_win_byts", "flow_duration")
    terms = []
    for name in fields:
        x = finite(name)
        terms.append(
            f"named_struct('feature', '{name}', 'records', count(*), 'nulls', count_if({name} IS NULL), "
            f"'nan', count_if(isnan({name})), 'infinities', count_if(abs({name}) = CAST('Infinity' AS DOUBLE)), "
            f"'minus_one', count_if({name} = -1D), 'finite_values', count({x}), 'finite_mean', avg({x}))"
        )
    return (f"SELECT '{layer}' AS layer, binary_label, m.* FROM (SELECT binary_label, explode(array({', '.join(terms)})) AS m "
            f"FROM {layer} GROUP BY binary_label) ORDER BY binary_label, m.feature")
