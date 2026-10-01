# FinSight

## Portfolio Health Intelligence Platform

> **Make every investment make sense.**

FinSight is an AI-powered Portfolio Health Intelligence Platform designed to help investors understand their portfolio beyond simple profit and loss.

The platform analyzes portfolio performance, risk, diversification, and investor behaviour to generate a comprehensive Portfolio Health Score and provide data-driven insights.

---

## Problem

Many investors primarily focus on returns while overlooking important aspects of portfolio management such as:

- Risk exposure
- Portfolio diversification
- Asset and sector concentration
- Risk-return balance
- Investment behaviour
- Emotional decision-making

FinSight aims to bring these factors together into one simple and intelligent platform.

---

## Solution

FinSight analyzes a user's portfolio and provides:

- Portfolio Health Score
- Portfolio performance analysis
- Risk analysis
- Diversification analysis
- Behaviour analysis
- Opinion vs Reality analysis
- AI-generated insights
- Data-driven areas to review

---

## Core Features

### 📊 Portfolio Dashboard

Provides an overview of:

- Total invested value
- Current portfolio value
- Profit/Loss
- Return percentage
- Portfolio Health Score

### 🛡️ Risk Analysis

Analyzes:

- Portfolio risk
- Volatility
- Concentration
- Sector exposure
- Individual holding exposure

### 📈 Diversification Analysis

Analyzes portfolio distribution across:

- Stocks
- Sectors
- Asset classes
- Individual holdings

### 🧠 Behaviour Analysis

Identifies potential patterns such as:

- Overtrading
- Frequent buying and selling
- Panic selling
- Holding losing positions
- Excessive concentration

### 🔍 Opinion vs Reality

Allows users to compare their perception of their portfolio with quantitative portfolio data.

### 🤖 AI Insights

Converts portfolio analysis into simple, understandable explanations and data-driven areas to review.

---

## System Architecture

```text
                         USER
                           │
                           ▼
                  ┌─────────────────┐
                  │ React Frontend  │
                  └────────┬────────┘
                           │
                        REST API
                           │
                           ▼
                  ┌─────────────────┐
                  │ FastAPI Backend │
                  └────────┬────────┘
                           │
             ┌─────────────┼─────────────┐
             │             │             │
             ▼             ▼             ▼
        Portfolio       Risk        Behaviour
        Analytics      Engine         Engine
             │             │             │
             └─────────────┼─────────────┘
                           │
                           ▼
                  ┌─────────────────┐
                  │ Health Score    │
                  │ Engine          │
                  └────────┬────────┘
                           │
                           ▼
                  ┌─────────────────┐
                  │ AI Insights     │
                  │ Engine          │
                  └────────┬────────┘
                           │
                           ▼
                  ┌─────────────────┐
                  │ Database        │
                  └─────────────────┘