# Microsoft Cloud Monitoring Domain Analysis

Detector-only threshold: `0.85`

| Domain | Windows | Candidates | Precision | Recall | F1 | FPR | FP | FN |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| application-crash-rate-1 | 5352 | 1329 | 0.4432 | 0.8068 | 0.5721 | 0.1601 | 740 | 141 |
| application-crash-rate-2 | 11011 | 1965 | 0.2046 | 0.7053 | 0.3172 | 0.1497 | 1563 | 168 |
| consumer-purchase-rate | 7488 | 2386 | 0.0532 | 0.7427 | 0.0993 | 0.3087 | 2259 | 44 |
| data-ingress-rate | 1320 | 1153 | 0.0278 | 1.0 | 0.054 | 0.8703 | 1121 | 0 |
| ecommerce-api-incoming-rps | 6191 | 2049 | 0.0517 | 0.8833 | 0.0977 | 0.32 | 1943 | 14 |
| middle-tier-api-dependency-latency | 16560 | 4462 | 0.1105 | 0.8915 | 0.1966 | 0.248 | 3969 | 60 |
| mongodb-application-rps | 1056 | 1004 | 0.0209 | 1.0 | 0.041 | 0.9498 | 983 | 0 |
| mongodb-machine-rps | 336 | 336 | 0.0714 | 1.0 | 0.1333 | 1.0 | 312 | 0 |
| service-unavailable | 264 | 2 | 0.0 | 0.0 | 0.0 | 0.0076 | 2 | 0 |

Domains with no positive anomaly windows use `0.0` recall/F1 by denominator convention; use them only to inspect false-positive behavior.
