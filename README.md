# FinSight — Portfolio Health Intelligence Platform

> **Make every investment make sense.**

FinSight is a **Portfolio Health Intelligence Platform** designed to help retail and beginner investors understand the overall health of their investment portfolio through **portfolio analytics, risk analysis, diversification analysis, behavioural analysis, and AI-powered insights**.

---

## 📑 Table of Contents

- [Project Overview](#-project-overview)
- [Problem Statement](#-problem-statement)
- [Project Opportunity](#-project-opportunity)
- [Solution](#-solution)
- [Objectives](#-objectives)
- [Target Users](#-target-users)
- [Core Features](#-core-features)
- [How FinSight Works](#-how-finsight-works)
- [Portfolio Health Score](#-portfolio-health-score)
- [AI Insight Engine](#-ai-insight-engine)
- [System Architecture](#-system-architecture)
- [Technology Stack](#-technology-stack)
- [Project Structure](#-project-structure)
- [Team & Responsibilities](#-team--responsibilities)
- [GitHub Workflow](#-github-workflow)
- [Development Roadmap](#-development-roadmap)
- [API Structure](#-api-structure)
- [Data Structure](#-data-structure)
- [Database Structure](#-database-structure)
- [Testing Strategy](#-testing-strategy)
- [Future Scope](#-future-scope)
- [Project Status](#-project-status)
- [Security](#-security)
- [Disclaimer](#-disclaimer)
- [Academic Context](#-academic-context)
- [Team](#-team)

---

# 🚀 Project Overview

**FinSight** is a portfolio intelligence platform that evaluates an investor's portfolio beyond simple returns.

Traditional portfolio tracking mainly answers:

> **"How much money did I make?"**

FinSight aims to answer:

> **"How healthy is my portfolio, what risks am I taking, how diversified am I, and what patterns should I pay attention to?"**

The platform combines quantitative portfolio analysis with behavioural analysis and AI-generated explanations.

FinSight focuses on:

- Portfolio performance
- Portfolio risk
- Diversification
- Asset allocation
- Concentration
- Investment behaviour
- Portfolio health
- AI-powered insights

---

# ❗ Problem Statement

Many investors focus heavily on portfolio returns while overlooking:

- Risk
- Diversification
- Asset allocation
- Concentration
- Investment behaviour
- Emotional decision-making

Common behavioural patterns can include:

- Panic selling
- Overtrading
- Holding losing positions
- Excessive concentration
- Reacting emotionally to short-term market movements

These factors can affect long-term portfolio management and investment behaviour.

FinSight addresses this problem by combining portfolio performance, risk, diversification, and behaviour analysis into a single platform.

---

# 💡 Project Opportunity

There is an opportunity to build a **Portfolio Health Intelligence Platform** for retail investors and traders who need better visibility into:

- Portfolio risk
- Diversification
- Portfolio performance
- Concentration
- Investment behaviour

FinSight converts raw portfolio data into understandable analytical information and AI-powered explanations.

---

# 🎯 Solution

FinSight evaluates an investment portfolio across multiple dimensions.

```text
                    PORTFOLIO DATA
                          |
          +---------------+---------------+
          |               |               |
          v               v               v
   +--------------+ +--------------+ +--------------+
   |  Portfolio   | |     Risk     | |  Behaviour   |
   |  Analytics   | |   Analysis   | |   Analysis   |
   +------+-------+ +------+-------+ +------+-------+
          |               |               |
          +---------------+---------------+
                          |
                          v
                 +------------------+
                 | Portfolio Health |
                 |      Score       |
                 +--------+---------+
                          |
                          v
                 +------------------+
                 |  AI Insight      |
                 |     Engine       |
                 +--------+---------+
                          |
                          v
                 +------------------+
                 | User Dashboard   |
                 |   & Insights     |
                 +------------------+
```

---

# 🎯 Objectives

The main objectives of FinSight are:

- Analyze portfolio performance
- Calculate portfolio returns
- Analyze asset allocation
- Identify portfolio concentration
- Evaluate portfolio risk
- Analyze diversification
- Identify behavioural patterns
- Generate a Portfolio Health Score
- Explain financial metrics in simple language
- Generate AI-powered portfolio insights
- Highlight data-driven areas that users may want to review
- Provide an easy-to-use portfolio dashboard

---

# 👥 Target Users

FinSight is primarily designed for:

### Retail Investors

Individuals managing their own investment portfolios.

### Beginner Investors

Users who may not have extensive knowledge of portfolio analysis.

### Young Investors

Gen Z and millennial investors who want an easier way to understand portfolio data.

### Active Investors

Investors who make frequent transactions and may benefit from behavioural analysis.

---

# ⚙️ Core Features

## 1. Portfolio Dashboard

The dashboard provides an overview of:

- Total portfolio value
- Invested amount
- Current value
- Overall P&L
- Return percentage
- Number of holdings
- Portfolio allocation
- Risk indicators
- Portfolio Health Score

---

## 2. Portfolio Upload

Users can upload portfolio data using a CSV file.

Example:

```csv
Symbol,Company,Quantity,Buy Price,Current Price
RELIANCE,Reliance Industries,10,2400,2650
TCS,Tata Consultancy Services,5,3500,4100
INFY,Infosys,8,1500,1650
```

The backend processes the uploaded data and sends it to the relevant analytical modules.

---

## 3. Holdings Analysis

The platform displays:

- Stock symbol
- Company
- Quantity
- Average buy price
- Current price
- Invested value
- Current value
- Profit/Loss
- Return %

---

## 4. Portfolio Performance

FinSight calculates:

- Invested capital
- Current portfolio value
- Absolute P&L
- Percentage return
- Individual stock performance
- Portfolio-level performance

---

## 5. Asset Allocation

The platform can visualize allocation across:

- Equity
- Other supported asset types
- Sectors
- Individual securities

Charts can include:

- Pie charts
- Donut charts
- Bar charts
- Allocation tables

---

## 6. Risk Analysis

The Risk Engine can analyze metrics such as:

- Portfolio volatility
- Concentration
- Maximum drawdown
- Individual stock contribution
- Sector concentration
- Risk-return relationship

---

## 7. Diversification Analysis

FinSight identifies:

- Number of holdings
- Sector exposure
- Top holding concentration
- Sector concentration
- Portfolio distribution
- Potential diversification gaps

---

## 8. Behaviour Analysis

FinSight analyzes transaction history to identify patterns such as:

- Frequent trading
- Overtrading indicators
- Panic-selling patterns
- Holding behaviour
- Buy/sell frequency
- Trading concentration

---

## 9. Portfolio Health Score

The Portfolio Health Score combines multiple analytical dimensions into a single portfolio-level indicator.

```text
              Portfolio Health
                     |
       +-------------+-------------+
       |             |             |
       v             v             v
  Performance      Risk      Diversification
       |             |             |
       +-------------+-------------+
                     |
                     v
              Behaviour Analysis
                     |
                     v
             Health Score Engine
                     |
                     v
            Portfolio Health Score
```

The scoring methodology will be defined and documented during development.

---

# 🤖 AI Insight Engine

The AI layer is responsible for explaining analytical results in simple language.

The AI engine should **not independently calculate financial metrics**.

Instead, the system follows:

```text
Portfolio Data
      |
      v
Portfolio Analytics
      |
      v
Risk Engine
      |
      v
Behaviour Engine
      |
      v
Health Score Engine
      |
      v
Structured Results
      |
      v
AI Insight Engine
      |
      v
Natural Language Insights
```

### Example

The analytics engine calculates:

```text
Top holding concentration = 42%
Sector concentration = 58%
```

The AI engine can then explain:

> A significant portion of the portfolio is concentrated in a small number of holdings and sectors. Changes in these positions may therefore have a relatively large effect on overall portfolio performance.

This separation keeps financial calculations within deterministic analytical modules while using AI primarily for interpretation and explanation.

---

# 🏗️ System Architecture

```text
                         USER
                           |
                           v
                 +------------------+
                 | React Frontend   |
                 | Vite + Tailwind  |
                 +--------+---------+
                          |
                          | REST API
                          v
                 +------------------+
                 | FastAPI Backend  |
                 +--------+---------+
                          |
          +---------------+---------------+
          |               |               |
          v               v               v
   +--------------+ +--------------+ +--------------+
   |  Portfolio   | |     Risk     | |  Behaviour   |
   |  Analytics   | |    Engine    | |    Engine    |
   +------+-------+ +------+-------+ +------+-------+
          |               |               |
          +---------------+---------------+
                          |
                          v
                 +------------------+
                 | Health Score     |
                 | Engine           |
                 +--------+---------+
                          |
                          v
                 +------------------+
                 | AI Insight       |
                 | Engine           |
                 +--------+---------+
                          |
                          v
                 +------------------+
                 | Dashboard / UI   |
                 +------------------+
```

---

# 🛠️ Technology Stack

## Frontend

| Technology | Purpose |
|---|---|
| React | Frontend framework |
| Vite | Development and build tool |
| Tailwind CSS | UI styling |
| Recharts | Data visualization |
| Axios | API communication |

## Backend

| Technology | Purpose |
|---|---|
| Python | Backend programming |
| FastAPI | REST API framework |
| Pandas | Data processing |
| NumPy | Numerical calculations |
| scikit-learn | Statistical/analytical functionality |
| Pydantic | Data validation |
| Uvicorn | Application server |

## Database

**SQLite**

SQLite will be used during the prototype stage for application-level data storage.

## Development Tools

- Git
- GitHub
- VS Code
- GitHub Pull Requests

---

# 📁 Project Structure

```text
FinSight/
│
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   ├── pages/
│   │   ├── charts/
│   │   ├── services/
│   │   ├── hooks/
│   │   ├── App.jsx
│   │   └── main.jsx
│   │
│   ├── public/
│   ├── package.json
│   └── vite.config.js
│
├── backend/
│   ├── api/
│   │   ├── portfolio.py
│   │   ├── risk.py
│   │   ├── behavior.py
│   │   ├── insights.py
│   │   └── health.py
│   │
│   ├── models/
│   ├── schemas/
│   ├── services/
│   ├── database/
│   ├── main.py
│   └── config.py
│
├── analytics/
│   ├── portfolio_metrics.py
│   ├── performance.py
│   ├── allocation.py
│   └── calculations.py
│
├── risk_engine/
│   ├── risk_metrics.py
│   ├── concentration.py
│   ├── diversification.py
│   └── risk_score.py
│
├── behavior/
│   ├── transaction_analysis.py
│   ├── trading_frequency.py
│   ├── panic_selling.py
│   └── behavior_score.py
│
├── ai/
│   ├── insight_engine.py
│   ├── prompts.py
│   └── response_formatter.py
│
├── data/
│   ├── sample_portfolio.csv
│   └── sample_transactions.csv
│
├── tests/
│   ├── test_analytics.py
│   ├── test_risk.py
│   ├── test_behavior.py
│   ├── test_api.py
│   └── test_health_score.py
│
├── docs/
│   ├── architecture.md
│   ├── api.md
│   └── data_dictionary.md
│
├── .gitignore
├── requirements.txt
├── README.md
└── LICENSE
```

---

# 👨‍💻 Team & Responsibilities

| Member | Role | Branch |
|---|---|---|
| **Ricky Maishari** | Frontend & UI | `feature/frontend` |
| **Jash Vora** | Backend & API | `feature/backend` |
| **Aditya Shah** | Portfolio Analytics | `feature/portfolio-analytics` |
| **Soumil Patro** | Risk & Diversification | `feature/risk` |
| **Prisha Mistry** | Behaviour Analysis | `feature/behavior` |
| **Rayyan Chunawala** | AI & Insights | `feature/ai` |
| **Atharva Suryavanshi** | Data, Testing & Integration | `feature/data-testing` |

---

## 1. Ricky Maishari — Frontend & UI

### Responsibilities

- React application setup
- Dashboard UI
- Portfolio overview
- Holdings table
- Risk visualization
- Allocation charts
- Health Score UI
- Insights page
- Responsive design
- API integration
- Loading and error states
- Reusable UI components

### Main Folder

```text
frontend/
```

### Branch

```text
feature/frontend
```

---

## 2. Jash Vora — Backend & API

### Responsibilities

- FastAPI setup
- API routing
- Portfolio upload endpoint
- Portfolio data processing
- Backend services
- Request/response schemas
- Integration of analytics modules
- Integration of risk engine
- Integration of behaviour engine
- Integration of AI engine
- Error handling
- Backend architecture

### Main Folder

```text
backend/
```

### Branch

```text
feature/backend
```

---

## 3. Aditya Shah — Portfolio Analytics

### Responsibilities

- Portfolio value calculation
- Invested value
- Current value
- Profit/Loss
- Return %
- Individual stock performance
- Portfolio performance
- Asset allocation
- Sector allocation
- Portfolio-level metrics

### Main Folder

```text
analytics/
```

### Branch

```text
feature/portfolio-analytics
```

---

## 4. Soumil Patro — Risk & Diversification

### Responsibilities

- Volatility calculations
- Concentration analysis
- Sector concentration
- Diversification metrics
- Drawdown analysis
- Risk contribution
- Risk score
- Risk-related API outputs
- Risk methodology documentation

### Main Folder

```text
risk_engine/
```

### Branch

```text
feature/risk
```

---

## 5. Prisha Mistry — Behaviour Analysis

### Responsibilities

- Transaction analysis
- Trading frequency
- Buy/sell patterns
- Holding duration
- Overtrading indicators
- Panic-selling indicators
- Behavioural metrics
- Behaviour score
- Behaviour-related API outputs

### Main Folder

```text
behavior/
```

### Branch

```text
feature/behavior
```

---

## 6. Rayyan Chunawala — AI & Insights

### Responsibilities

- AI integration
- Insight generation
- Prompt design
- Financial metric explanation
- Portfolio summary generation
- Risk explanation
- Diversification explanation
- Behavioural insight generation
- Opinion vs Reality section
- Structured AI responses

### Main Folder

```text
ai/
```

### Branch

```text
feature/ai
```

---

## 7. Atharva Suryavanshi — Data, Testing & Integration

### Responsibilities

- Sample datasets
- Data validation
- Data cleaning
- Test cases
- Unit testing
- API testing
- Integration testing
- End-to-end testing
- Bug tracking
- Final integration
- Prototype stability

### Main Folders

```text
data/
tests/
```

### Branch

```text
feature/data-testing
```

---

# 🌿 GitHub Workflow

FinSight uses:

```text
main
```

as the stable branch.

There is **no `dev` branch**.

Each team member works on their assigned feature branch.

```text
                         main
                          |
       +------------------+------------------+
       |         |        |        |         |
       v         v        v        v         v
   frontend   backend   analytics  risk   behavior
       |         |        |        |         |
       +---------+--------+--------+---------+
                          |
                    Pull Requests
                          |
                          v
                         main
```

---

## Branches

```text
feature/frontend
feature/backend
feature/portfolio-analytics
feature/risk
feature/behavior
feature/ai
feature/data-testing
```

---

## Standard Git Workflow

First update your local `main`:

```bash
git checkout main
git pull origin main
```

Create or switch to your feature branch:

```bash
git checkout -b feature/your-feature
```

After making changes:

```bash
git add .
```

Commit your changes:

```bash
git commit -m "Add portfolio analytics calculations"
```

Push your branch:

```bash
git push -u origin feature/your-feature
```

Then create a **Pull Request** from your feature branch into:

```text
main
```

After review and testing, the Pull Request can be merged.

---

# 🗺️ Development Roadmap

## Phase 1 — Project Setup

### Tasks

- Create GitHub repository
- Create project structure
- Create README
- Configure `.gitignore`
- Configure Python environment
- Configure React/Vite
- Configure FastAPI
- Install dependencies
- Establish branch structure

**Status:** 🟡 In Progress

---

## Phase 2 — Data Layer

### Tasks

- Define portfolio CSV format
- Define transaction CSV format
- Create sample portfolio
- Create sample transaction data
- Data validation
- Data cleaning
- Define database schema

**Primary Members:**

Atharva + Jash

---

## Phase 3 — Portfolio Analytics

### Tasks

- Portfolio value
- Invested value
- Current value
- P&L
- Returns
- Stock-level analysis
- Allocation
- Sector exposure

**Primary Member:**

Aditya

---

## Phase 4 — Risk & Diversification

### Tasks

- Volatility
- Concentration
- Diversification
- Sector concentration
- Drawdown
- Risk score

**Primary Member:**

Soumil

---

## Phase 5 — Behaviour Analysis

### Tasks

- Transaction frequency
- Buy/sell patterns
- Holding periods
- Overtrading indicators
- Panic-selling indicators
- Behaviour score

**Primary Member:**

Prisha

---

## Phase 6 — Portfolio Health Score

### Tasks

- Define scoring methodology
- Normalize metrics
- Calculate individual components
- Generate overall Health Score
- Generate score explanation

```text
Portfolio Analytics
        +
Risk Analysis
        +
Diversification
        +
Behaviour Analysis
        |
        v
Health Score Engine
        |
        v
Portfolio Health Score
```

**Coordination:**

Aditya + Soumil + Prisha + Jash

---

## Phase 7 — AI Insights

### Tasks

- AI integration
- Prompt engineering
- Structured input format
- Insight generation
- Portfolio summary
- Risk explanation
- Behaviour explanation
- Data-driven areas to review

**Primary Member:**

Rayyan

---

## Phase 8 — Frontend

### Tasks

- Dashboard
- Portfolio upload
- Holdings
- Performance charts
- Allocation charts
- Risk section
- Behaviour section
- Health Score
- AI Insights

**Primary Member:**

Ricky

---

## Phase 9 — Backend Integration

### Tasks

Connect all modules:

```text
Frontend
   |
   v
FastAPI
   |
   v
Analytics
   |
   v
Risk
   |
   v
Behaviour
   |
   v
Health Score
   |
   v
AI
   |
   v
Frontend Response
```

**Primary Members:**

Jash + Atharva

---

## Phase 10 — Testing

### Testing Areas

- Unit testing
- API testing
- Data validation
- Calculation testing
- Integration testing
- UI testing
- Error handling
- Edge cases
- End-to-end testing

**Primary Member:**

Atharva

---

## Phase 11 — Final Prototype

### Tasks

- Fix bugs
- Improve UI
- Improve performance
- Complete documentation
- Test complete user journey
- Prepare demo dataset
- Prepare presentation
- Prepare project demonstration

**Responsibility:**

Entire Team

---

# 🔌 API Structure

| Method | Endpoint | Purpose |
|---|---|---|
| `POST` | `/api/portfolio/upload` | Upload portfolio |
| `GET` | `/api/portfolio/summary` | Portfolio summary |
| `GET` | `/api/portfolio/holdings` | Holdings |
| `GET` | `/api/portfolio/performance` | Performance |
| `GET` | `/api/portfolio/allocation` | Asset allocation |
| `GET` | `/api/portfolio/risk` | Risk analysis |
| `GET` | `/api/portfolio/diversification` | Diversification |
| `GET` | `/api/portfolio/behavior` | Behaviour analysis |
| `GET` | `/api/portfolio/health` | Health Score |
| `GET` | `/api/portfolio/insights` | AI insights |

---

# 📊 Data Structure

## Portfolio CSV

```text
portfolio_id
symbol
company_name
asset_type
sector
quantity
average_buy_price
current_price
```

Example:

```csv
portfolio_id,symbol,company_name,asset_type,sector,quantity,average_buy_price,current_price
P001,RELIANCE,Reliance Industries,Equity,Energy,10,2400,2650
P001,TCS,Tata Consultancy Services,Equity,IT,5,3500,4100
P001,INFY,Infosys,Equity,IT,8,1500,1650
```

---

## Transactions CSV

```text
transaction_id
portfolio_id
date
symbol
transaction_type
quantity
price
```

Example:

```csv
transaction_id,portfolio_id,date,symbol,transaction_type,quantity,price
T001,P001,2026-01-10,RELIANCE,BUY,10,2400
T002,P001,2026-02-12,TCS,BUY,5,3500
T003,P001,2026-03-15,INFY,BUY,8,1500
```

---

# 🗄️ Database Structure

## Users

```text
users
----------------
id
name
email
created_at
```

## Portfolios

```text
portfolios
----------------
id
user_id
name
created_at
```

## Holdings

```text
holdings
----------------
id
portfolio_id
symbol
company_name
asset_type
sector
quantity
average_buy_price
current_price
```

## Transactions

```text
transactions
----------------
id
portfolio_id
date
symbol
transaction_type
quantity
price
```

Future tables:

```text
analysis_results
health_scores
user_preferences
```

---

# 🧪 Testing Strategy

## Unit Testing

Individual calculations will be tested separately.

Examples:

```text
P&L calculation
Return calculation
Allocation calculation
Risk calculation
Health Score calculation
```

---

## API Testing

Important endpoints will be tested:

```text
POST /api/portfolio/upload
GET /api/portfolio/summary
GET /api/portfolio/risk
GET /api/portfolio/health
```

---

## Integration Testing

The complete flow will be tested:

```text
Frontend
   |
Backend
   |
Analytics
   |
Risk
   |
Behaviour
   |
Health Score
   |
AI
```

---

## Edge Cases

The application should handle:

- Empty CSV
- Invalid CSV
- Missing columns
- Zero quantity
- Missing prices
- Duplicate transactions
- Invalid values
- Large portfolios
- Single-stock portfolios
- Empty transaction history

---

# 🔐 Security

API keys and credentials must **never** be committed to GitHub.

Use:

```text
.env
```

for local secrets.

Example:

```env
AI_API_KEY=your_api_key
DATABASE_URL=your_database_url
```

The `.env` file must remain in `.gitignore`.

A safe template can be provided as:

```text
.env.example
```

---

# 🚀 Future Scope

Potential future features include:

### Broker Integration

Connect portfolios directly with supported brokerage platforms.

### Live Market Data

Integrate market-data APIs for updated prices.

### Advanced AI Assistant

Allow users to ask questions about their portfolio.

Example:

```text
Why did my portfolio return decrease this month?
```

### Portfolio Q&A

Users could ask:

```text
Which sector has the highest exposure?
```

```text
What percentage of my portfolio is concentrated
in my top holdings?
```

### Advanced Risk Analytics

Potential future metrics include:

- Sharpe Ratio
- Beta
- Alpha
- Value at Risk
- Correlation
- Stress Testing

### Portfolio Monitoring

Future versions could monitor portfolio changes and provide updated analytical summaries.

---

# 📌 Project Status

| Component | Owner | Status |
|---|---|---|
| Project Setup | Entire Team | 🟡 In Progress |
| GitHub Repository | Entire Team | 🟢 Completed |
| README | Entire Team | 🟢 Completed |
| Frontend | Ricky | 🔴 Not Started |
| Backend | Jash | 🔴 Not Started |
| Portfolio Analytics | Aditya | 🔴 Not Started |
| Risk Engine | Soumil | 🔴 Not Started |
| Behaviour Engine | Prisha | 🔴 Not Started |
| AI Engine | Rayyan | 🔴 Not Started |
| Data & Testing | Atharva | 🔴 Not Started |
| Integration | Entire Team | 🔴 Not Started |
| Final Prototype | Entire Team | 🔴 Not Started |

### Status Legend

```text
🟢 Completed
🟡 In Progress
🔴 Not Started
```

---

# 📚 Documentation

Additional technical documentation can be maintained inside:

```text
docs/
```

Recommended documentation:

```text
docs/
├── architecture.md
├── api.md
├── data_dictionary.md
├── analytics_methodology.md
├── risk_methodology.md
├── behavior_methodology.md
└── testing.md
```

The **README.md remains the primary overview of the entire FinSight project**.

---

# ⚠️ Disclaimer

FinSight is an **academic/student prototype** created for educational and demonstration purposes.

The platform provides analytical information and data-driven insights based on available portfolio data.

It should not be treated as personalized financial, investment, tax, or legal advice.

Users should independently evaluate financial decisions and consult an appropriately qualified professional where necessary.

---

# 🎓 Academic Context

**Project:** Portfolio Health Intelligence Platform

**Product Name:** FinSight

**Course:** Design Experience Course — Entrepreneurship Vertical

**Program:** B.Tech Computer Science Engineering and Business Systems

**Semester:** IV

**Academic Year:** 2025–26

---

# 👨‍👩‍👧‍👦 Team

| Name | Roll No. | Responsibility |
|---|---|---|
| **Rayyan Chunawala** | E014 | AI & Insights |
| **Ricky Maishari** | E037 | Frontend & UI |
| **Prisha Mistry** | E042 | Behaviour Analysis |
| **Soumil Patro** | E050 | Risk & Diversification |
| **Aditya Shah** | E062 | Portfolio Analytics |
| **Atharva Suryavanshi** | E065 | Data, Testing & Integration |
| **Jash Vora** | E067 | Backend & API |

---

# 🌟 Vision

> **Make every investment make sense.**

FinSight aims to transform raw portfolio data into understandable intelligence by bringing together:

```text
Performance
     +
Risk
     +
Diversification
     +
Behaviour
     +
AI
     |
     v
Portfolio Health Intelligence
```

The goal is to help users understand **what is happening in their portfolio, what the data indicates, and which areas deserve attention**.

---

# 📜 License

This project is developed as an academic project by the **FinSight team**.

---

<div align="center">

### FinSight

**Portfolio Health Intelligence Platform**

**Make every investment make sense.**

</div>