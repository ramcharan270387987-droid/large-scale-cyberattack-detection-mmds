# Observed attack-pattern candidates

These retrospective comparisons use the saved labels and full eligible feature support for each statistic. The rule cutoffs are descriptive approximate quantiles of benign traffic in the same capture collection. Use them as hypotheses for held-out evaluation. [Threshold values](../reports/phase3_reference_thresholds.csv)

| Pattern | Benign matches / eligible | Attack matches / eligible | Benign share | Attack share |
| --- | --- | --- | --- | --- |
| high_mean_iat | 135,684 / 13,484,694 | 2,545 / 2,748,235 | 1.006% | 0.093% |
| high_packet_rate | 16,676 / 13,390,235 | 183 / 2,746,934 | 0.125% | 0.007% |
| large_packet_count | 134,952 / 13,484,708 | 4,348 / 2,748,235 | 1.001% | 0.158% |
| short_high_bytes | 8 / 13,484,694 | 0 / 2,748,235 | 0.000% | 0.000% |

Every rule matched benign records at least as often as attack records among its eligible rows. The short-duration, high-byte rule produced particularly few matches. These results favor investigating family-specific context and comparing feature distributions before choosing candidate indicators.

High packet rate and large packet count used strict values above benign P99 (2e+06 packets/s and 70 packets). Short high-byte flows used duration at or below benign P10 (74 µs) and bytes above benign P99 (3.142e+04 bytes). High mean inter-arrival time used benign P99 (8.625e+07 µs). [Patterns by family](../reports/phase3_candidate_patterns.csv)

## Selected correlations

| Pair | Benign Pearson r | Attack Pearson r | Benign pairs | Attack pairs |
| --- | --- | --- | --- | --- |
| `flow_duration` · `total_bytes` | 0.04637 | 0.2472 | 13,484,694 | 2,748,235 |
| `flow_duration` · `total_packets` | 0.07053 | 0.2449 | 13,484,694 | 2,748,235 |
| `flow_iat_mean` · `flow_duration` | 0.4936 | 0.6887 | 13,484,694 | 2,748,235 |
| `pkt_len_mean` · `total_bytes` | 0.1721 | 0.01477 | 13,484,708 | 2,748,235 |
| `syn_flag_cnt` · `rst_flag_cnt` | -0.1091 | -0.0391 | 13,484,708 | 2,748,235 |
| `tot_fwd_pkts` · `tot_bwd_pkts` | 0.7612 | -0.001627 | 13,484,708 | 2,748,235 |
| `total_packets` · `total_bytes` | 0.9818 | 0.9863 | 13,484,708 | 2,748,235 |
| `totlen_fwd_pkts` · `totlen_bwd_pkts` | 0.004782 | 0.0002273 | 13,484,708 | 2,748,235 |

Counts and bytes share a mechanical volume relationship, and flow duration and inter-arrival summaries share timing information. Correlations describe the observed rows. Family composition, repeated traffic and heavy tails can affect their magnitude.

## TCP flags and transport context

| Class | Leading family-specific TCP flag tuple | Records |
| --- | --- | --- |
| benign | Benign · ACK | 3,118,001 |
| attack | DDoS · ACK | 808,367 |

The most common observed destination ports were 80.0 for attack (1,784,942 records), 53.0 for benign (4,021,224 records). Ports and flag tuples can reflect the laboratory scenario and protocol composition. [TCP flags](../reports/phase3_tcp_flags.csv) · [Ports by family](../reports/phase3_destination_ports.csv)
