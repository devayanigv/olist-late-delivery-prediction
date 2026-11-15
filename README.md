# Olist E-Commerce: Late Delivery Prediction & Data Warehouse

An end-to-end data analytics, machine learning, and data warehousing project using the Brazilian E-Commerce Public Dataset by Olist.

## 1. Project Overview

This project investigates late deliveries in Brazilian e-commerce using machine learning and PostgreSQL.

It combines:
- Exploratory data analysis and data quality checks.
- Feature engineering and late-delivery classification.
- SQL analytics and statistical testing.
- A PostgreSQL star-schema data warehouse.
- A Python ETL pipeline to populate and validate warehouse tables.

## 2. Dataset

Dataset source: Brazilian E-Commerce Public Dataset by Olist (Kaggle)
https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce

The dataset contains approximately 100,000 orders and related customer, product, seller, payment, review, and delivery information.

Original dataset tables include:
- Customers
- Orders
- Order items
- Products
- Sellers
- Payments
- Reviews
- Geolocation
- Product category translation

The dataset was used for educational and non-commercial purposes. Please refer to its CC BY-NC-SA 4.0 license and attribution requirements.

## 3. Project Architecture

```text
Olist CSV Dataset
       |
       v
PostgreSQL - raw schema
       |
       v
PostgreSQL - analytics schema
       |
       v
Python ETL Pipeline
       |
       v
PostgreSQL - warehouse schema
       |
       v
Star Schema
  |             |
  v             v
Dimension      Fact
Tables         Tables
       |
       v
SQL Analytics and Reporting
```

The machine learning workflow is developed separately in the project notebook.

## 4. Project Components

### A. Late Delivery Prediction

The machine learning component:
- Explores and cleans the Olist dataset.
- Performs feature engineering using order and delivery information.
- Uses a chronological train/test split.
- Trains Logistic Regression and Random Forest classifiers.
- Evaluates models using accuracy, precision, recall, F1-score, and ROC-AUC.
- Investigates classification threshold tuning to address class imbalance.

Late deliveries are relatively uncommon, so accuracy alone is not sufficient to assess model performance.

### B. PostgreSQL Data Warehouse

Three PostgreSQL schemas are used:

| Schema | Purpose |
|---|---|
| `raw` | Stores source dataset tables |
| `analytics` | Contains SQL transformations and analytical views |
| `warehouse` | Contains dimensional and fact tables |

Analytical views include:
- `analytics.order_item_summary`
- `analytics.payment_summary`
- `analytics.review_summary`
- `analytics.order_level_base`

### C. Star Schema Design

The warehouse contains four dimension tables and two fact tables.

| Table | Grain | Primary Key | Business Key / Foreign Keys |
|---|---|---|---|
| `dim_date` | One row per calendar date | `date_key` | `full_date` (unique) |
| `dim_customer` | One row per customer | `customer_key` | `customer_id` (unique) |
| `dim_product` | One row per product | `product_key` | `product_id` (unique) |
| `dim_seller` | One row per seller | `seller_key` | `seller_id` (unique) |
| `fact_orders` | One row per order | `order_key` | `order_id` (unique); customer and date foreign keys |
| `fact_order_items` | One row per order item | `order_item_key` | Order, customer, product, seller, and date foreign keys |

**Fact table measures include:**
- Total items per order
- Total product value
- Total freight value
- Payment value
- Actual delivery days
- Late-delivery indicator

The order-item fact table stores item-level price and freight values.

## 5. ETL Pipeline

The ETL implementation is located at:

`src/etl/run_pipeline.py`

The pipeline:
1. Connects to PostgreSQL through a SQLAlchemy engine.
2. Clears existing warehouse data as part of a full-refresh load.
3. Loads customer, product, and seller dimensions.
4. Generates a continuous date dimension.
5. Loads the order-level fact table.
6. Loads the order-item fact table.
7. Validates expected row counts and referential integrity.

The pipeline uses a database transaction so that validation failures roll back the load.

**Important:** This is a full-refresh pipeline, not an incremental load. The source `raw` tables must already be populated before execution.

## 6. Data Quality and Validation

Data quality checks were performed on source data and warehouse tables.

Checks included:
- Primary and business key uniqueness.
- Null and missing-value checks.
- Foreign key and orphan-record validation.
- Duplicate order-item checks.
- Invalid timestamps.
- Negative prices and freight values.
- Review score range validation.
- Product attribute validation.

### Warehouse validation results

| Table | Expected / Actual Rows |
|---|---:|
| `dim_customer` | 99,441 |
| `dim_seller` | 3,095 |
| `dim_product` | 32,951 |
| `dim_date` | 1,315 |
| `fact_orders` | 99,441 |
| `fact_order_items` | 112,650 |

Additional validation confirmed:
- No duplicate order-item business keys.
- No orphaned fact-table foreign keys.
- Fact order-item totals reconcile with order-level item totals for product value and freight.

## 7. Repository Structure

```text
olist-late-delivery-prediction/
│
├── notebooks/
│   └── Olist_Late_Delivery_Prediction.ipynb
│
├── sql/
│   └── warehouse/
│       └── create_schema.sql
│
├── src/
│   └── etl/
│       └── run_pipeline.py
│
├── reports/
│
├── requirements.txt
├── README.md
└── .gitignore
```

## 8. Setup and Reproducibility

### Prerequisites

- Python 3
- PostgreSQL database
- Git
- Access to the Olist dataset

### Step 1: Clone the repository

```bash
git clone https://github.com/devayanigv/olist-late-delivery-prediction.git

cd olist-late-delivery-prediction
```

### Step 2: Install dependencies

```bash
pip install -r requirements.txt
```

### Step 3: Prepare the database

1. Create or connect to a PostgreSQL database.
2. Create and populate the `raw` schema using the Olist CSV files.
3. Execute the relevant SQL scripts to create the analytics and warehouse structures.
4. Ensure the raw source tables are available before running the ETL pipeline.

### Step 4: Configure database connection

Set your PostgreSQL connection string through an environment variable named `DATABASE_URL`.

Do not commit database credentials or passwords to GitHub.

### Step 5: Run the ETL pipeline

The ETL function accepts a SQLAlchemy engine. It can be invoked from Python as follows:

```python
import os
import sys

from sqlalchemy import create_engine

database_url = os.environ["DATABASE_URL"]

engine_url = database_url.replace(
    "postgresql://",
    "postgresql+psycopg2://",
    1
)

engine = create_engine(engine_url, pool_pre_ping=True)

sys.path.append(os.path.abspath("src/etl"))

from run_pipeline import run_pipeline

pipeline_counts = run_pipeline(engine)

print(pipeline_counts)
```

The pipeline performs a full refresh of the warehouse tables and validates the resulting data.

### Step 6: Explore the notebook

Open:

`notebooks/Olist_Late_Delivery_Prediction.ipynb`

The notebook contains the exploratory analysis, feature engineering, statistical analysis, model training, and evaluation workflow. It was developed in Google Colab.

## 9. Technologies Used

| Area | Tools |
|---|---|
| Programming | Python |
| Data manipulation | Pandas, NumPy |
| Machine learning | Scikit-learn |
| Visualization | Matplotlib, Seaborn |
| Statistical analysis | SciPy |
| Database | PostgreSQL |
| Database connectivity | SQLAlchemy, psycopg2 |
| Development environment | Google Colab |
| Version control | Git, GitHub |

## 10. Future Improvements

- Add incremental ETL loading.
- Automate raw CSV ingestion.
- Add automated data quality tests.
- Compare query performance with and without indexes.
- Add further analytical SQL reports and dashboards.
- Improve model performance and evaluate additional classification approaches.

## 11. Author and Repository

**GitHub Repository:**  
https://github.com/devayanigv/olist-late-delivery-prediction

