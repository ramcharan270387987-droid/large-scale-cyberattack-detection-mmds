"""Capture-day and eligible local wall-clock summaries."""

FAMILY_DAY_SQL = """SELECT d.source_day, f.attack_family, coalesce(o.records, 0) AS records
 FROM (SELECT DISTINCT source_day FROM traffic) d
 CROSS JOIN (SELECT DISTINCT attack_family FROM traffic WHERE binary_label = 1) f
 LEFT JOIN (SELECT source_day, attack_family, count(*) AS records FROM traffic WHERE binary_label = 1
 GROUP BY source_day, attack_family) o
 ON d.source_day = o.source_day AND f.attack_family = o.attack_family
 ORDER BY d.source_day, f.attack_family"""

HOURLY_SQL = """SELECT source_day, hour(parsed_event_time) AS local_hour, count(*) AS records,
 count_if(binary_label = 0) AS benign, count_if(binary_label = 1) AS attacks,
 avg(CAST(binary_label AS DOUBLE)) AS attack_share,
 avg(flow_duration) AS mean_duration_us, avg(total_packets) AS mean_packets, avg(total_bytes) AS mean_bytes,
 count(flow_duration) AS duration_observations, count(total_packets) AS packet_observations,
 count(total_bytes) AS byte_observations
 FROM traffic WHERE temporal_eligibility
 GROUP BY source_day, hour(parsed_event_time) ORDER BY source_day, local_hour"""

WINDOW_SQL = """SELECT source_day, population, floor(hour(parsed_event_time) / 3) * 3 AS window_start_hour,
 count(*) AS records, count(flow_duration) AS duration_observations, count(total_packets) AS packet_observations,
 count(total_bytes) AS byte_observations, percentile_approx(flow_duration, 0.5D, {accuracy}) AS median_duration_us,
 percentile_approx(total_packets, 0.5D, {accuracy}) AS median_packets,
 percentile_approx(total_bytes, 0.5D, {accuracy}) AS median_bytes
 FROM traffic WHERE temporal_eligibility
 GROUP BY source_day, population, floor(hour(parsed_event_time) / 3) ORDER BY source_day, window_start_hour, population"""
