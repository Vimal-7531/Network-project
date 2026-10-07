# Network Operations Predictive Intelligence System

An end-to-end telecom data engineering, analytics, machine learning, and network operations intelligence platform built using Python, PySpark, Apache Airflow, FastAPI, React, and Machine Learning.

The project processes large-scale telecom activity data from Milan, transforms raw network activity into analytics-ready datasets, orchestrates reliable data pipelines, exposes operational intelligence through REST APIs, visualizes network activity through an interactive NOC dashboard, and generates predictive network risk scores.

---

## Project Overview

Telecommunication networks generate large volumes of activity data across different geographic regions and time periods. Raw network activity alone is difficult for operations teams to interpret and prioritize.

This project builds an end-to-end **Network Operations Predictive Intelligence System** that converts raw telecom activity into operational insights.

The system supports:

- Telecom activity ingestion
- Data validation and cleaning
- Distributed PySpark processing
- Hourly grid-level aggregation
- Geographic enrichment
- Data pipeline orchestration
- Data quality monitoring
- Analytics warehouse generation
- REST API access
- Interactive NOC dashboard
- Hotspot and alert visualization
- Grid-level activity exploration
- Machine-learning feature engineering
- Network anomaly detection
- Predictive network risk scoring

---

## System Architecture

```text
                Telecom Activity CSV Files
                          |
                          v
                 +------------------+
                 |   Data Landing   |
                 +------------------+
                          |
                          v
                 +------------------+
                 |    Ingestion     |
                 |      DE2         |
                 +------------------+
                          |
                          v
                 +------------------+
                 | PySpark Pipeline |
                 |   Cleaning       |
                 |   Aggregation    |
                 |   Enrichment     |
                 +------------------+
                          |
               +----------+----------+
               |                     |
               v                     v
        Processed Data        Analytics Data
          Parquet            Hourly Grid Summary
               |                     |
               +----------+----------+
                          |
                          v
                 +------------------+
                 | Machine Learning |
                 | Feature Pipeline |
                 +------------------+
                          |
              +-----------+-----------+
              |                       |
              v                       v
       Anomaly Detection       Risk Prediction
              |                       |
              +-----------+-----------+
                          |
                          v
                 +------------------+
                 | Data Warehouse   |
                 +------------------+
                          |
                          v
                 +------------------+
                 |     FastAPI      |
                 |  REST Services   |
                 +------------------+
                          |
                          v
              +------------------------+
              | React NOC Dashboard    |
              |                        |
              | Overview               |
              | Grid Explorer          |
              | Hotspots & Alerts      |
              | Milan Grid Map         |
              | Predictive Risk        |
              +------------------------+

                Apache Airflow
                     |
                     v
         Orchestrates the complete pipeline
```

---

# Project Phases

The project was developed incrementally across multiple phases.

## Phase 1 — Core Python

Phase 1 establishes the basic telecom data processing workflow using Python.

### NP1 — Dataset Profiling

Explores the telecom dataset and identifies:

- Dataset structure
- Column types
- Missing values
- Activity distributions
- Timestamp coverage
- Grid coverage

### NP2 — Usage Processor

Processes daily telecom activity and generates reusable summaries.

Outputs include:

- Daily activity summaries
- Grid-level summaries

### NP3 — Rule-Based Network Alerts

Introduces rule-based operational alert generation based on telecom activity patterns.

This establishes the initial network monitoring layer before machine-learning models are introduced.

---

## Phase 2 — Distributed Processing with PySpark

Phase 2 moves processing from local Python operations to distributed data processing using PySpark.

### SP1 — Distributed Ingestion

Reads multiple daily telecom datasets using Spark.

### SP2 — Cleaning and Standardization

Performs:

- Schema validation
- Missing-value handling
- Data standardization
- Invalid record handling

### SP3 — Grid and Hour Aggregation

Transforms raw telecom records into hourly grid-level network activity.

### SP4 — Geographic Enrichment

Enriches telecom activity using the Milan grid GeoJSON reference.

The geographic join uses:

```text
properties.cellId
```

to correctly map telecom grid IDs to geographic cells.

### SP5 — Performance Experiments

Evaluates Spark execution and processing behavior.

### SP6 — Analytics Output

Produces analytics-ready Parquet datasets.

### SP7 — Reusable Telecom Pipeline

Combines ingestion, cleaning, aggregation, geographic enrichment, and output generation into a reusable Spark ETL pipeline.

---

## Phase 3 — Data Engineering

Phase 3 converts the Spark processing workflow into a production-style data engineering pipeline.

### Data Architecture

```text
Landing
   |
   v
Raw
   |
   v
Processed
   |
   v
Analytics
   |
   v
Warehouse
```

### DE1 — Data Layer Architecture

Defines the project's multi-layer data architecture.

### DE2 — Reliable Ingestion

Implements controlled file ingestion with:

- Validation
- Duplicate protection
- Audit logging
- Accepted/rejected file handling

### DE3 — Spark ETL Integration

Integrates the PySpark processing pipeline into the data engineering workflow.

### DE4 / DE5 — Pipeline Processing

Extends transformation and analytics processing across the data layers.

### DE6 — Analytics Warehouse

Loads curated network analytics into a warehouse for downstream API consumption.

### DE7 — Data Quality Validation

Performs quality checks such as:

- Duplicate detection
- Required-field validation
- Pipeline output verification
- Data quality status tracking

### DE8 — Pipeline Reliability

Introduces:

- Failure handling
- Safe reruns
- Pipeline status tracking
- Operational logging

---

# Apache Airflow Orchestration

Apache Airflow orchestrates the end-to-end data and machine-learning pipeline.

The integrated DAG contains the following workflow:

```text
run_de2_ingestion
        |
        v
run_de3_spark
        |
        v
run_ml2_features
        |
        v
run_ml6_scoring
        |
        v
run_validation
        |
        v
load_warehouse
        |
        v
quality_check
        |
        v
notify
        |
        v
pipeline_status
```

This provides centralized orchestration and visibility into pipeline execution.

---

# Phase 4 — FastAPI Service Layer

FastAPI exposes processed network intelligence through REST APIs.

## API Endpoints

| Method | Endpoint | Purpose |
|---|---|---|
| GET | `/network/summary` | Network-wide operational summary |
| GET | `/network/grid/{grid_id}` | Grid-level hourly activity |
| GET | `/network/hotspots` | Highest-priority network hotspots |
| GET | `/network/alerts` | Operational network alerts |
| GET | `/network/grid/{grid_id}/location` | Geographic grid information |
| POST | `/network/predict-risk` | Predictive risk scoring |
| GET | `/pipeline/status` | Data pipeline health/status |

Interactive API documentation is provided through Swagger.

```text
http://127.0.0.1:8000/docs
```

---

# Phase 5 — React Network Operations Dashboard

The frontend provides a Network Operations Center style interface for exploring network intelligence.

## Overview Dashboard

Displays network-level operational metrics obtained directly from the FastAPI service.

The dashboard provides a quick view of current network activity and reporting status.

## Grid Explorer

Allows operators to search for a specific Milan grid ID and inspect its hourly activity.

Displayed metrics include:

- SMS activity
- Call activity
- Internet activity
- Total activity

## Hotspots

Displays grids with significant operational activity and prioritizes areas that may require attention.

## Alerts

Displays network alerts separately from hotspots so operators can distinguish activity concentration from operational alert conditions.

## Interactive Milan Grid Map

The dashboard integrates Leaflet with the Milan GeoJSON grid.

Instead of displaying all 10,000 geographic cells simultaneously, the operational map focuses on grids associated with current:

- Hotspots
- Alerts

Grid polygons are joined using:

```text
properties.cellId
```

Users can interact with the geographic cells and navigate to the corresponding Grid Explorer.

## Predictive Risk

Allows operators to request machine-learning risk predictions for a specific grid and timestamp.

The interface displays:

- Risk score
- Risk level
- Model version
- Supporting anomaly information

Model predictions are presented as predictive indicators rather than confirmed network faults.

---

# Phase 6 — Machine Learning

The machine-learning phase adds predictive intelligence to the network monitoring platform.

## ML1 — Dataset Preparation

Prepares analytics data for machine-learning workflows.

## ML2 — Feature Engineering

Generates model-ready features from historical network activity.

Features are derived from grid-level and temporal network behavior.

## ML3 — Risk Model

A supervised machine-learning model estimates network operational risk.

The model produces:

```text
Risk Score
Risk Level
Model Version
```

Risk levels support operational prioritization.

## ML4 — Anomaly Detection

Detects unusual activity by comparing current grid behavior with historical patterns.

The anomaly layer provides additional context for predictive risk results.

## ML5 — Model Evaluation

Evaluates model performance and validates predictive behavior.

## ML6 — Batch Risk Scoring

Runs risk scoring across network activity data and produces operational risk outputs for downstream services.

---

# Data Model

The project works with telecom communication activity across Milan geographic grid cells.

Important activity dimensions include:

```text
SMS In
SMS Out
Call In
Call Out
Internet Activity
```

A project-defined composite metric is also generated:

```text
Total Activity
```

`total_activity` is an analytical activity indicator and should not be interpreted as bandwidth utilization, congestion percentage, message count, or network throughput.

---

# Geographic Data

Milan is divided into **10,000 geographic grid cells**.

The GeoJSON reference contains geographic polygons for these cells.

Correct mapping is performed using:

```text
feature.properties.cellId
```

rather than the GeoJSON top-level feature ID.

This ensures network activity is associated with the correct geographic location.

---

# Technology Stack

## Programming

- Python
- JavaScript
- SQL

## Data Engineering

- Pandas
- PySpark
- Apache Spark
- Apache Airflow
- Parquet
- SQLite

## Backend

- FastAPI
- Pydantic
- Uvicorn

## Machine Learning

- Scikit-learn
- Feature Engineering
- Logistic Regression
- Anomaly Detection
- Batch Scoring

## Frontend

- React
- Vite
- React Leaflet
- Leaflet
- OpenStreetMap

## Development Tools

- Git
- GitHub
- VS Code
- Windows
- WSL

---

# Project Structure

```text
network_project/
│
├── airflow/
│   └── dags/
│
├── data/
│   ├── landing/
│   ├── raw/
│   ├── processed/
│   ├── analytics/
│   └── reference/
│
├── logs/
│
├── phase1/
│   ├── np1_profile_telecom.py
│   ├── usage_processor.py
│   └── network_alerts.py
│
├── phase2/
│   ├── sp1_distributed_ingestion.py
│   ├── sp2_cleaning.py
│   ├── sp3_aggregations.py
│   ├── sp4_enrichment.py
│   ├── sp5_performance_experiments.py
│   ├── sp6_write_outputs.py
│   └── sp7_telecom_pipeline.py
│
├── phase3/
│   ├── ingestion/
│   ├── quality/
│   ├── spark/
│   ├── validation/
│   └── warehouse/
│
├── phase4/
│   ├── api/
│   └── services/
│
├── phase5/
│   └── frontend/
│       ├── public/
│       │   └── reference/
│       └── src/
│           ├── components/
│           └── pages/
│
├── phase6/
│   └── ml/
│
├── .gitignore
└── README.md
```

---

# Running the Project

## 1. Clone the Repository

```bash
git clone <repository-url>
cd network_project
```

---

## 2. Python Environment

Create and activate a Python virtual environment.

### Windows

```cmd
python -m venv myenv
myenv\Scripts\activate
```

Install the required Python dependencies for the project.

---

## 3. Run the FastAPI Backend

From the project root:

```cmd
uvicorn phase4.api.main:app --reload
```

The API will be available at:

```text
http://127.0.0.1:8000
```

Swagger documentation:

```text
http://127.0.0.1:8000/docs
```

---

## 4. Run the React Frontend

Open another terminal:

```cmd
cd phase5\frontend
npm install
npm run dev
```

Open the URL displayed by Vite, typically:

```text
http://localhost:5173
```

---

## 5. Run Machine-Learning Batch Scoring

From the project root:

```cmd
python phase6\ml\batch_score.py
```

---

# Example Operational Flow

A typical end-to-end flow is:

```text
Telecom Data
     |
     v
Ingestion
     |
     v
Validation
     |
     v
PySpark Processing
     |
     v
Hourly Grid Analytics
     |
     v
ML Feature Engineering
     |
     v
Risk + Anomaly Scoring
     |
     v
Analytics Warehouse
     |
     v
FastAPI
     |
     v
React NOC Dashboard
     |
     +--> Overview
     +--> Grid Explorer
     +--> Hotspots
     +--> Alerts
     +--> Milan Map
     +--> Predictive Risk
```

---

# Key Engineering Features

The project demonstrates several production-oriented engineering concepts:

- Layered data architecture
- Distributed processing
- Reusable ETL pipelines
- Idempotent processing
- Duplicate protection
- Data validation gates
- Pipeline audit logging
- Airflow orchestration
- Safe pipeline reruns
- Analytics warehouse design
- REST API architecture
- Frontend/backend separation
- Geographic visualization
- Machine-learning integration
- Batch prediction
- Operational risk prioritization

---

# Important Interpretation Notes

The dataset represents **communication activity**, not direct network performance measurements.

Therefore:

- High activity does not automatically mean congestion.
- A high risk score does not confirm a network fault.
- Internet activity is not equivalent to bandwidth usage.
- SMS and call activity values should not be interpreted as literal message or call counts.
- `total_activity` is a project-defined analytical indicator.
- ML outputs are predictive indicators intended to assist operational prioritization.

---

# Future Enhancements

Potential extensions include:

- Real-time streaming ingestion
- Kafka integration
- Live network telemetry
- Advanced time-series forecasting
- Automated incident correlation
- Model monitoring and drift detection
- Explainable AI
- AI-assisted network operations
- Automated root-cause analysis
- Cloud deployment
- Containerization with Docker
- Production-grade monitoring and observability

---

# Project Goal

The goal of this project is not simply to build an ML model or dashboard independently.

It demonstrates how:

**Data Engineering + Distributed Processing + APIs + Machine Learning + Visualization**

can be combined into a complete operational intelligence system.

The final platform transforms large-scale telecom activity data into actionable network insights that can help operations teams identify important areas, investigate grid-level behavior, detect anomalies, and prioritize predictive network risks.

---

## Author

**Vimalraj C K**

Network Operations Predictive Intelligence System
