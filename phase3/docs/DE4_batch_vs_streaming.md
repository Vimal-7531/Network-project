# DE4 — Batch vs Streaming Decision Workshop

## Project

Network Operations & Predictive Intelligence System

## Objective

Evaluate whether different network operations workloads should be processed using batch processing or streaming.

The current training dataset consists of daily CSV files containing hourly network activity observations. It is therefore processed as batch data.

## Decision Matrix

| Workload | Source | Arrival Pattern | Required Latency | Decision | Reason |
|---|---|---|---|---|---|
| Daily usage summary | Daily network activity CSV | Once per day | 1–24 hours | Batch | Results do not need real-time updates |
| Hypothetical live activity events | Network event stream | Continuous | Seconds | Streaming | Operations may need immediate visibility |
| Billing report | Billing records | Daily/monthly | Hours to days | Batch | Billing is periodic and does not require second-level processing |
| Hotspot alerts | Network activity events | Current dataset is daily batch | Minutes to hours | Batch for this project | The training data arrives as daily files, so streaming would add complexity without useful benefit |
| Executive dashboard refresh | Analytics layer | Periodic | Minutes to hours | Batch | Dashboard can refresh after the analytics pipeline completes |
| Model training | Historical analytics data | Periodic | Hours | Batch | Training uses accumulated historical data |
| Model scoring | New network events | Continuous in production | Seconds to minutes | Streaming in a future architecture | Real-time scoring could require immediate predictions |

## Why This Project Uses Batch Processing

The dataset consists of daily activity files containing hourly observations.

Although real telecom networks generate activity continuously, this training dataset does not provide a continuous event stream.

Therefore, implementing Kafka or Spark Streaming would introduce additional infrastructure and operational complexity without providing meaningful value for the current dataset.

The current architecture is:

Raw daily CSV files
→ Ingestion
→ PySpark processing
→ Processed data
→ Analytics
→ API
→ Dashboard

## Where Streaming Could Enter

A future production architecture could introduce a streaming path:

Network events
→ Kafka
→ Streaming processing
→ Real-time analytics
→ Alerts / Real-time scoring

The streaming path is optional and is not implemented in this project.

The existing batch pipeline would remain useful for:

- Historical analytics
- Daily reporting
- Model training
- Backfills
- Reprocessing
- Periodic dashboard refreshes

## Batch vs Streaming Trade-off

### Batch Advantages

- Simpler architecture
- Lower operational complexity
- Easier debugging
- Suitable for daily files
- Lower infrastructure requirements
- Reproducible processing

### Streaming Advantages

- Low latency
- Continuous processing
- Suitable for real-time alerts
- Suitable for real-time scoring
- Faster operational response

### Why Streaming Is Not Used Here

Streaming would add infrastructure and operational cost without adding sufficient value because the source data arrives as daily files.

Therefore:

**Batch is the correct engineering choice for the current training dataset.**

## Final Architecture Decision

The project will remain batch-based.

A future streaming extension may be added when the source becomes a genuine continuous event stream and the business requires second-level or minute-level processing.

Kafka could conceptually be placed between the network event source and the processing layer in that future architecture.

## Example Future Architecture

Network Events
        |
        v
      Kafka
        |
        v
Streaming Processing
        |
        +------> Real-time Alerts
        |
        +------> Real-time Scoring

Historical / Daily Files
        |
        v
Batch PySpark Pipeline
        |
        +------> Analytics
        |
        +------> Reporting
        |
        +------> Model Training