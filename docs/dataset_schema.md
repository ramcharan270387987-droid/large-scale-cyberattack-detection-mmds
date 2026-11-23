# MMDS dataset schema

Kaggle version 1 returned readable headers for 10 of 10 expected captures. Column indices are zero-based. Header strings are shown in JSON notation to preserve whitespace.

The most common original header, from `Wednesday-14-02-2018_TrafficForML_CICFlowMeter.csv`, is the reference for comparisons.

| File | Columns | Feature candidates | Label index | Timestamp index | Same normalized order | Exact original header | Normalized schema compatible | Extra | Missing | Duplicate names | Whitespace / encoding |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Wednesday-14-02-2018_TrafficForML_CICFlowMeter.csv | 80 | 78 | 79 | 2 | True | True | True | — | — | — | 0 whitespace, 0 non-ASCII |
| Thursday-15-02-2018_TrafficForML_CICFlowMeter.csv | 80 | 78 | 79 | 2 | True | True | True | — | — | — | 0 whitespace, 0 non-ASCII |
| Friday-16-02-2018_TrafficForML_CICFlowMeter.csv | 80 | 78 | 79 | 2 | True | True | True | — | — | — | 0 whitespace, 0 non-ASCII |
| Thuesday-20-02-2018_TrafficForML_CICFlowMeter.csv | 84 | 82 | 83 | 6 | False | False | False | flow_id, src_ip, src_port, dst_ip | — | — | 0 whitespace, 0 non-ASCII |
| Wednesday-21-02-2018_TrafficForML_CICFlowMeter.csv | 80 | 78 | 79 | 2 | True | True | True | — | — | — | 0 whitespace, 0 non-ASCII |
| Thursday-22-02-2018_TrafficForML_CICFlowMeter.csv | 80 | 78 | 79 | 2 | True | True | True | — | — | — | 0 whitespace, 0 non-ASCII |
| Friday-23-02-2018_TrafficForML_CICFlowMeter.csv | 80 | 78 | 79 | 2 | True | True | True | — | — | — | 0 whitespace, 0 non-ASCII |
| Wednesday-28-02-2018_TrafficForML_CICFlowMeter.csv | 80 | 78 | 79 | 2 | True | True | True | — | — | — | 0 whitespace, 0 non-ASCII |
| Thursday-01-03-2018_TrafficForML_CICFlowMeter.csv | 80 | 78 | 79 | 2 | True | True | True | — | — | — | 0 whitespace, 0 non-ASCII |
| Friday-02-03-2018_TrafficForML_CICFlowMeter.csv | 80 | 78 | 79 | 2 | True | True | True | — | — | — | 0 whitespace, 0 non-ASCII |

## Original header 1

`Wednesday-14-02-2018_TrafficForML_CICFlowMeter.csv`, `Thursday-15-02-2018_TrafficForML_CICFlowMeter.csv`, `Friday-16-02-2018_TrafficForML_CICFlowMeter.csv`, `Wednesday-21-02-2018_TrafficForML_CICFlowMeter.csv`, `Thursday-22-02-2018_TrafficForML_CICFlowMeter.csv`, `Friday-23-02-2018_TrafficForML_CICFlowMeter.csv`, `Wednesday-28-02-2018_TrafficForML_CICFlowMeter.csv`, `Thursday-01-03-2018_TrafficForML_CICFlowMeter.csv`, `Friday-02-03-2018_TrafficForML_CICFlowMeter.csv`

| Index | Original | Normalized | Profile candidates |
| --- | --- | --- | --- |
| 0 | `"Dst Port"` | `dst_port` | numeric |
| 1 | `"Protocol"` | `protocol` | categorical |
| 2 | `"Timestamp"` | `timestamp` | timestamp |
| 3 | `"Flow Duration"` | `flow_duration` | numeric |
| 4 | `"Tot Fwd Pkts"` | `tot_fwd_pkts` | numeric |
| 5 | `"Tot Bwd Pkts"` | `tot_bwd_pkts` | numeric |
| 6 | `"TotLen Fwd Pkts"` | `totlen_fwd_pkts` | numeric |
| 7 | `"TotLen Bwd Pkts"` | `totlen_bwd_pkts` | numeric |
| 8 | `"Fwd Pkt Len Max"` | `fwd_pkt_len_max` | numeric |
| 9 | `"Fwd Pkt Len Min"` | `fwd_pkt_len_min` | numeric |
| 10 | `"Fwd Pkt Len Mean"` | `fwd_pkt_len_mean` | numeric |
| 11 | `"Fwd Pkt Len Std"` | `fwd_pkt_len_std` | numeric |
| 12 | `"Bwd Pkt Len Max"` | `bwd_pkt_len_max` | numeric |
| 13 | `"Bwd Pkt Len Min"` | `bwd_pkt_len_min` | numeric |
| 14 | `"Bwd Pkt Len Mean"` | `bwd_pkt_len_mean` | numeric |
| 15 | `"Bwd Pkt Len Std"` | `bwd_pkt_len_std` | numeric |
| 16 | `"Flow Byts/s"` | `flow_byts_s` | numeric |
| 17 | `"Flow Pkts/s"` | `flow_pkts_s` | numeric |
| 18 | `"Flow IAT Mean"` | `flow_iat_mean` | numeric |
| 19 | `"Flow IAT Std"` | `flow_iat_std` | numeric |
| 20 | `"Flow IAT Max"` | `flow_iat_max` | numeric |
| 21 | `"Flow IAT Min"` | `flow_iat_min` | numeric |
| 22 | `"Fwd IAT Tot"` | `fwd_iat_tot` | numeric |
| 23 | `"Fwd IAT Mean"` | `fwd_iat_mean` | numeric |
| 24 | `"Fwd IAT Std"` | `fwd_iat_std` | numeric |
| 25 | `"Fwd IAT Max"` | `fwd_iat_max` | numeric |
| 26 | `"Fwd IAT Min"` | `fwd_iat_min` | numeric |
| 27 | `"Bwd IAT Tot"` | `bwd_iat_tot` | numeric |
| 28 | `"Bwd IAT Mean"` | `bwd_iat_mean` | numeric |
| 29 | `"Bwd IAT Std"` | `bwd_iat_std` | numeric |
| 30 | `"Bwd IAT Max"` | `bwd_iat_max` | numeric |
| 31 | `"Bwd IAT Min"` | `bwd_iat_min` | numeric |
| 32 | `"Fwd PSH Flags"` | `fwd_psh_flags` | numeric |
| 33 | `"Bwd PSH Flags"` | `bwd_psh_flags` | numeric |
| 34 | `"Fwd URG Flags"` | `fwd_urg_flags` | numeric |
| 35 | `"Bwd URG Flags"` | `bwd_urg_flags` | numeric |
| 36 | `"Fwd Header Len"` | `fwd_header_len` | numeric |
| 37 | `"Bwd Header Len"` | `bwd_header_len` | numeric |
| 38 | `"Fwd Pkts/s"` | `fwd_pkts_s` | numeric |
| 39 | `"Bwd Pkts/s"` | `bwd_pkts_s` | numeric |
| 40 | `"Pkt Len Min"` | `pkt_len_min` | numeric |
| 41 | `"Pkt Len Max"` | `pkt_len_max` | numeric |
| 42 | `"Pkt Len Mean"` | `pkt_len_mean` | numeric |
| 43 | `"Pkt Len Std"` | `pkt_len_std` | numeric |
| 44 | `"Pkt Len Var"` | `pkt_len_var` | numeric |
| 45 | `"FIN Flag Cnt"` | `fin_flag_cnt` | numeric |
| 46 | `"SYN Flag Cnt"` | `syn_flag_cnt` | numeric |
| 47 | `"RST Flag Cnt"` | `rst_flag_cnt` | numeric |
| 48 | `"PSH Flag Cnt"` | `psh_flag_cnt` | numeric |
| 49 | `"ACK Flag Cnt"` | `ack_flag_cnt` | numeric |
| 50 | `"URG Flag Cnt"` | `urg_flag_cnt` | numeric |
| 51 | `"CWE Flag Count"` | `cwe_flag_count` | numeric |
| 52 | `"ECE Flag Cnt"` | `ece_flag_cnt` | numeric |
| 53 | `"Down/Up Ratio"` | `down_up_ratio` | numeric |
| 54 | `"Pkt Size Avg"` | `pkt_size_avg` | numeric |
| 55 | `"Fwd Seg Size Avg"` | `fwd_seg_size_avg` | numeric |
| 56 | `"Bwd Seg Size Avg"` | `bwd_seg_size_avg` | numeric |
| 57 | `"Fwd Byts/b Avg"` | `fwd_byts_b_avg` | numeric |
| 58 | `"Fwd Pkts/b Avg"` | `fwd_pkts_b_avg` | numeric |
| 59 | `"Fwd Blk Rate Avg"` | `fwd_blk_rate_avg` | numeric |
| 60 | `"Bwd Byts/b Avg"` | `bwd_byts_b_avg` | numeric |
| 61 | `"Bwd Pkts/b Avg"` | `bwd_pkts_b_avg` | numeric |
| 62 | `"Bwd Blk Rate Avg"` | `bwd_blk_rate_avg` | numeric |
| 63 | `"Subflow Fwd Pkts"` | `subflow_fwd_pkts` | numeric |
| 64 | `"Subflow Fwd Byts"` | `subflow_fwd_byts` | numeric |
| 65 | `"Subflow Bwd Pkts"` | `subflow_bwd_pkts` | numeric |
| 66 | `"Subflow Bwd Byts"` | `subflow_bwd_byts` | numeric |
| 67 | `"Init Fwd Win Byts"` | `init_fwd_win_byts` | numeric |
| 68 | `"Init Bwd Win Byts"` | `init_bwd_win_byts` | numeric |
| 69 | `"Fwd Act Data Pkts"` | `fwd_act_data_pkts` | numeric |
| 70 | `"Fwd Seg Size Min"` | `fwd_seg_size_min` | numeric |
| 71 | `"Active Mean"` | `active_mean` | numeric |
| 72 | `"Active Std"` | `active_std` | numeric |
| 73 | `"Active Max"` | `active_max` | numeric |
| 74 | `"Active Min"` | `active_min` | numeric |
| 75 | `"Idle Mean"` | `idle_mean` | numeric |
| 76 | `"Idle Std"` | `idle_std` | numeric |
| 77 | `"Idle Max"` | `idle_max` | numeric |
| 78 | `"Idle Min"` | `idle_min` | numeric |
| 79 | `"Label"` | `label` | label |

## Original header 2

`Thuesday-20-02-2018_TrafficForML_CICFlowMeter.csv`

| Index | Original | Normalized | Profile candidates |
| --- | --- | --- | --- |
| 0 | `"Flow ID"` | `flow_id` | identifier |
| 1 | `"Src IP"` | `src_ip` | identifier |
| 2 | `"Src Port"` | `src_port` | numeric |
| 3 | `"Dst IP"` | `dst_ip` | identifier |
| 4 | `"Dst Port"` | `dst_port` | numeric |
| 5 | `"Protocol"` | `protocol` | categorical |
| 6 | `"Timestamp"` | `timestamp` | timestamp |
| 7 | `"Flow Duration"` | `flow_duration` | numeric |
| 8 | `"Tot Fwd Pkts"` | `tot_fwd_pkts` | numeric |
| 9 | `"Tot Bwd Pkts"` | `tot_bwd_pkts` | numeric |
| 10 | `"TotLen Fwd Pkts"` | `totlen_fwd_pkts` | numeric |
| 11 | `"TotLen Bwd Pkts"` | `totlen_bwd_pkts` | numeric |
| 12 | `"Fwd Pkt Len Max"` | `fwd_pkt_len_max` | numeric |
| 13 | `"Fwd Pkt Len Min"` | `fwd_pkt_len_min` | numeric |
| 14 | `"Fwd Pkt Len Mean"` | `fwd_pkt_len_mean` | numeric |
| 15 | `"Fwd Pkt Len Std"` | `fwd_pkt_len_std` | numeric |
| 16 | `"Bwd Pkt Len Max"` | `bwd_pkt_len_max` | numeric |
| 17 | `"Bwd Pkt Len Min"` | `bwd_pkt_len_min` | numeric |
| 18 | `"Bwd Pkt Len Mean"` | `bwd_pkt_len_mean` | numeric |
| 19 | `"Bwd Pkt Len Std"` | `bwd_pkt_len_std` | numeric |
| 20 | `"Flow Byts/s"` | `flow_byts_s` | numeric |
| 21 | `"Flow Pkts/s"` | `flow_pkts_s` | numeric |
| 22 | `"Flow IAT Mean"` | `flow_iat_mean` | numeric |
| 23 | `"Flow IAT Std"` | `flow_iat_std` | numeric |
| 24 | `"Flow IAT Max"` | `flow_iat_max` | numeric |
| 25 | `"Flow IAT Min"` | `flow_iat_min` | numeric |
| 26 | `"Fwd IAT Tot"` | `fwd_iat_tot` | numeric |
| 27 | `"Fwd IAT Mean"` | `fwd_iat_mean` | numeric |
| 28 | `"Fwd IAT Std"` | `fwd_iat_std` | numeric |
| 29 | `"Fwd IAT Max"` | `fwd_iat_max` | numeric |
| 30 | `"Fwd IAT Min"` | `fwd_iat_min` | numeric |
| 31 | `"Bwd IAT Tot"` | `bwd_iat_tot` | numeric |
| 32 | `"Bwd IAT Mean"` | `bwd_iat_mean` | numeric |
| 33 | `"Bwd IAT Std"` | `bwd_iat_std` | numeric |
| 34 | `"Bwd IAT Max"` | `bwd_iat_max` | numeric |
| 35 | `"Bwd IAT Min"` | `bwd_iat_min` | numeric |
| 36 | `"Fwd PSH Flags"` | `fwd_psh_flags` | numeric |
| 37 | `"Bwd PSH Flags"` | `bwd_psh_flags` | numeric |
| 38 | `"Fwd URG Flags"` | `fwd_urg_flags` | numeric |
| 39 | `"Bwd URG Flags"` | `bwd_urg_flags` | numeric |
| 40 | `"Fwd Header Len"` | `fwd_header_len` | numeric |
| 41 | `"Bwd Header Len"` | `bwd_header_len` | numeric |
| 42 | `"Fwd Pkts/s"` | `fwd_pkts_s` | numeric |
| 43 | `"Bwd Pkts/s"` | `bwd_pkts_s` | numeric |
| 44 | `"Pkt Len Min"` | `pkt_len_min` | numeric |
| 45 | `"Pkt Len Max"` | `pkt_len_max` | numeric |
| 46 | `"Pkt Len Mean"` | `pkt_len_mean` | numeric |
| 47 | `"Pkt Len Std"` | `pkt_len_std` | numeric |
| 48 | `"Pkt Len Var"` | `pkt_len_var` | numeric |
| 49 | `"FIN Flag Cnt"` | `fin_flag_cnt` | numeric |
| 50 | `"SYN Flag Cnt"` | `syn_flag_cnt` | numeric |
| 51 | `"RST Flag Cnt"` | `rst_flag_cnt` | numeric |
| 52 | `"PSH Flag Cnt"` | `psh_flag_cnt` | numeric |
| 53 | `"ACK Flag Cnt"` | `ack_flag_cnt` | numeric |
| 54 | `"URG Flag Cnt"` | `urg_flag_cnt` | numeric |
| 55 | `"CWE Flag Count"` | `cwe_flag_count` | numeric |
| 56 | `"ECE Flag Cnt"` | `ece_flag_cnt` | numeric |
| 57 | `"Down/Up Ratio"` | `down_up_ratio` | numeric |
| 58 | `"Pkt Size Avg"` | `pkt_size_avg` | numeric |
| 59 | `"Fwd Seg Size Avg"` | `fwd_seg_size_avg` | numeric |
| 60 | `"Bwd Seg Size Avg"` | `bwd_seg_size_avg` | numeric |
| 61 | `"Fwd Byts/b Avg"` | `fwd_byts_b_avg` | numeric |
| 62 | `"Fwd Pkts/b Avg"` | `fwd_pkts_b_avg` | numeric |
| 63 | `"Fwd Blk Rate Avg"` | `fwd_blk_rate_avg` | numeric |
| 64 | `"Bwd Byts/b Avg"` | `bwd_byts_b_avg` | numeric |
| 65 | `"Bwd Pkts/b Avg"` | `bwd_pkts_b_avg` | numeric |
| 66 | `"Bwd Blk Rate Avg"` | `bwd_blk_rate_avg` | numeric |
| 67 | `"Subflow Fwd Pkts"` | `subflow_fwd_pkts` | numeric |
| 68 | `"Subflow Fwd Byts"` | `subflow_fwd_byts` | numeric |
| 69 | `"Subflow Bwd Pkts"` | `subflow_bwd_pkts` | numeric |
| 70 | `"Subflow Bwd Byts"` | `subflow_bwd_byts` | numeric |
| 71 | `"Init Fwd Win Byts"` | `init_fwd_win_byts` | numeric |
| 72 | `"Init Bwd Win Byts"` | `init_bwd_win_byts` | numeric |
| 73 | `"Fwd Act Data Pkts"` | `fwd_act_data_pkts` | numeric |
| 74 | `"Fwd Seg Size Min"` | `fwd_seg_size_min` | numeric |
| 75 | `"Active Mean"` | `active_mean` | numeric |
| 76 | `"Active Std"` | `active_std` | numeric |
| 77 | `"Active Max"` | `active_max` | numeric |
| 78 | `"Active Min"` | `active_min` | numeric |
| 79 | `"Idle Mean"` | `idle_mean` | numeric |
| 80 | `"Idle Std"` | `idle_std` | numeric |
| 81 | `"Idle Max"` | `idle_max` | numeric |
| 82 | `"Idle Min"` | `idle_min` | numeric |
| 83 | `"Label"` | `label` | label |

The parser preserves field order and assigns internal names by position. Normalized names are for comparison. Repeated or empty normalized names are flagged as unsupported for feature matching. Numeric candidates have at least 95% numeric lexical values among present cells, counting NaN and infinity as numeric tokens. IP and flow identifiers, protocol, labels and timestamps use their explicit roles. See the quality table for candidates that vary by capture. [Column profiles](../reports/dataset_quality_summary.csv)
