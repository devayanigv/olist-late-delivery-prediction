# Olist E-Commerce: Late Delivery Prediction & Data Warehouse

An end-to-end data analytics and machine learning project using the Brazilian E-Commerce Public Dataset by Olist.

## Project Overview

This project explores order delivery performance in Brazilian e-commerce. It combines machine learning and SQL data warehousing to predict late deliveries and analyze operational bottlenecks.

## Project Components

### 1. Late Delivery Prediction
- Explored and cleaned the Olist dataset.
- Engineered temporal, order-level, and logistics features.
- Trained and evaluated classification models (Logistic Regression, Random Forest) using ROC-AUC and threshold tuning.

### 2. Data Warehouse & SQL Analytics
- Built `raw` and `analytics` schemas in PostgreSQL (Neon).
- Created aggregated summary views (`order_item_summary`, `payment_summary`, `review_summary`, `order_level_base`).
- Performed statistical testing (Chi-square) and exploratory data analysis.
