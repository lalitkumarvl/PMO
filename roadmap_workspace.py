import math
import re
from datetime import date, datetime, timedelta
from io import BytesIO

import pandas as pd
import plotly.express as px
import streamlit as st
from fpdf import FPDF


ROADMAP_PHASES = [
    "Requirement Gathering",
    "Design",
    "Development",
    "Testing",
    "Deployment",
    "Post-Production Support",
]
PHASE_ORDER = {phase: index for index, phase in enumerate(ROADMAP_PHASES)}
SKILL_OPTIONS = ["Junior", "Mid", "Senior"]
BUILD_OPTIONS = ["Build from Scratch", "Reuse Existing Module"]
EXECUTION_OPTIONS = ["Sequential", "Parallel"]
RISK_PRIORITY = {"High": 3, "Medium": 2, "Low": 1}
SKILL_FACTOR = {"Junior": 1.18, "Mid": 1.0, "Senior": 0.88}

TEAM_GUIDANCE = {
    "UI/UX Design": "Own user journeys, visual hierarchy, and reusable design patterns.",
    "Frontend Development": "Drive web experience, state management, and interaction quality.",
    "Backend Development": "Own core business services, APIs, data rules, and integrations.",
    "DevOps": "Establish environments, release automation, and operational readiness.",
    "QA/Testing": "Cover functional, regression, and release-quality validation.",
    "Project Manager": "Run governance, cadence, dependencies, and stakeholder communication.",
    "Product Manager": "Shape scope, backlog, acceptance criteria, and value priorities.",
    "Security / Compliance": "Validate controls, policy alignment, and audit readiness.",
    "Data Engineering": "Support reporting, pipelines, analytics, and data quality.",
    "Business Analyst": "Clarify business rules, workflows, and requirements traceability.",
    "Support / Operations": "Prepare handover, hypercare, support readiness, and SLAs.",
}

TEAM_BASELINES = {
    "UI/UX Design": {"Low": 1, "Medium": 2, "High": 3},
    "Frontend Development": {"Low": 2, "Medium": 3, "High": 5},
    "Backend Development": {"Low": 2, "Medium": 3, "High": 5},
    "DevOps": {"Low": 1, "Medium": 1, "High": 2},
    "QA/Testing": {"Low": 1, "Medium": 2, "High": 3},
    "Project Manager": {"Low": 1, "Medium": 1, "High": 2},
    "Product Manager": {"Low": 1, "Medium": 1, "High": 2},
    "Security / Compliance": {"Low": 1, "Medium": 1, "High": 2},
    "Data Engineering": {"Low": 1, "Medium": 2, "High": 3},
    "Business Analyst": {"Low": 1, "Medium": 1, "High": 2},
    "Support / Operations": {"Low": 1, "Medium": 1, "High": 2},
}

TEAM_DEFAULT_SKILL = {
    "UI/UX Design": {"Low": "Mid", "Medium": "Mid", "High": "Senior"},
    "Frontend Development": {"Low": "Mid", "Medium": "Mid", "High": "Senior"},
    "Backend Development": {"Low": "Mid", "Medium": "Senior", "High": "Senior"},
    "DevOps": {"Low": "Mid", "Medium": "Senior", "High": "Senior"},
    "QA/Testing": {"Low": "Mid", "Medium": "Mid", "High": "Senior"},
    "Project Manager": {"Low": "Senior", "Medium": "Senior", "High": "Senior"},
    "Product Manager": {"Low": "Senior", "Medium": "Senior", "High": "Senior"},
    "Security / Compliance": {"Low": "Senior", "Medium": "Senior", "High": "Senior"},
    "Data Engineering": {"Low": "Mid", "Medium": "Senior", "High": "Senior"},
    "Business Analyst": {"Low": "Mid", "Medium": "Senior", "High": "Senior"},
    "Support / Operations": {"Low": "Mid", "Medium": "Mid", "High": "Senior"},
}

PROFILE_CATALOG = [
    {
        "id": "delivery_workspace",
        "name": "Delivery and workflow platform",
        "keywords": [
            "project",
            "roadmap",
            "workflow",
            "task",
            "ticket",
            "delivery",
            "kanban",
            "sprint",
            "portfolio",
            "agile",
        ],
        "products": [
            {
                "Product Name": "Jira Software",
                "Organization": "Atlassian",
                "Key differentiators": "Deep Agile workflow control, issue linking, and delivery reporting.",
            },
            {
                "Product Name": "Azure DevOps",
                "Organization": "Microsoft",
                "Key differentiators": "Boards, repos, pipelines, and enterprise governance in one stack.",
            },
            {
                "Product Name": "Monday.com",
                "Organization": "monday.com",
                "Key differentiators": "Flexible work management with faster business-team adoption.",
            },
        ],
        "modules": [
            ("Project intake and prioritization", "Product Manager", "Reuse Existing Module", 25, "Master data and intake form rules"),
            ("Backlog and sprint planning", "Frontend Development", "Build from Scratch", 0, "Workflow states and role permissions"),
            ("Execution board and approvals", "Backend Development", "Build from Scratch", 0, "Approval matrix and notification service"),
            ("Executive reporting and roadmap analytics", "Data Engineering", "Reuse Existing Module", 30, "Delivery dataset and dashboard model"),
            ("Notification and escalation engine", "Backend Development", "Reuse Existing Module", 20, "Email, Teams, or Slack connectors"),
        ],
        "additional_teams": ["Business Analyst", "Support / Operations"],
    },
    {
        "id": "service_management",
        "name": "Service and support platform",
        "keywords": [
            "service",
            "incident",
            "support",
            "helpdesk",
            "case",
            "ticketing",
            "sla",
            "operations",
        ],
        "products": [
            {
                "Product Name": "ServiceNow",
                "Organization": "ServiceNow",
                "Key differentiators": "Enterprise workflow automation with strong ITSM governance.",
            },
            {
                "Product Name": "Zendesk",
                "Organization": "Zendesk",
                "Key differentiators": "Fast support setup with strong omnichannel agent tooling.",
            },
            {
                "Product Name": "Freshservice",
                "Organization": "Freshworks",
                "Key differentiators": "IT service workflows with easier rollout for mid-size teams.",
            },
        ],
        "modules": [
            ("Request intake and triage", "Frontend Development", "Reuse Existing Module", 20, "Category taxonomy and intake forms"),
            ("Case routing and SLA automation", "Backend Development", "Build from Scratch", 0, "Priority rules and ownership matrix"),
            ("Knowledge base and self-service", "Frontend Development", "Reuse Existing Module", 25, "Content templates and search index"),
            ("Escalations and alerts", "Backend Development", "Reuse Existing Module", 20, "Messaging channels and support roster"),
            ("Operational dashboards", "Data Engineering", "Reuse Existing Module", 30, "Incident data model and SLA logic"),
        ],
        "additional_teams": ["Business Analyst", "Support / Operations"],
    },
    {
        "id": "commerce_platform",
        "name": "Digital commerce product",
        "keywords": [
            "ecommerce",
            "commerce",
            "cart",
            "checkout",
            "order",
            "payment",
            "catalog",
            "inventory",
        ],
        "products": [
            {
                "Product Name": "Shopify",
                "Organization": "Shopify",
                "Key differentiators": "Fast commerce launch with strong ecosystem and storefront tooling.",
            },
            {
                "Product Name": "Adobe Commerce",
                "Organization": "Adobe",
                "Key differentiators": "Enterprise merchandising, B2B features, and complex catalog support.",
            },
            {
                "Product Name": "Salesforce Commerce Cloud",
                "Organization": "Salesforce",
                "Key differentiators": "Unified customer context with large-enterprise commerce operations.",
            },
        ],
        "modules": [
            ("Catalog and product discovery", "Frontend Development", "Build from Scratch", 0, "Search, taxonomy, and media assets"),
            ("Cart and checkout flow", "Frontend Development", "Build from Scratch", 0, "Pricing rules and payment services"),
            ("Order management integration", "Backend Development", "Reuse Existing Module", 20, "ERP, OMS, or shipping adapters"),
            ("Payments and fraud controls", "Backend Development", "Reuse Existing Module", 15, "Gateway, tokenization, and audit trails"),
            ("Performance and analytics", "Data Engineering", "Reuse Existing Module", 25, "Order, funnel, and campaign data"),
        ],
        "additional_teams": ["Security / Compliance", "Business Analyst", "Support / Operations"],
    },
    {
        "id": "data_ai_platform",
        "name": "Data and AI product",
        "keywords": [
            "data",
            "dashboard",
            "analytics",
            "ai",
            "ml",
            "forecast",
            "insight",
            "reporting",
            "model",
        ],
        "products": [
            {
                "Product Name": "Power BI",
                "Organization": "Microsoft",
                "Key differentiators": "Strong enterprise reporting and Microsoft ecosystem fit.",
            },
            {
                "Product Name": "Tableau",
                "Organization": "Salesforce",
                "Key differentiators": "Rich visual exploration and analytics storytelling.",
            },
            {
                "Product Name": "Databricks",
                "Organization": "Databricks",
                "Key differentiators": "Unified data and AI engineering at platform scale.",
            },
        ],
        "modules": [
            ("Data ingestion and quality pipelines", "Data Engineering", "Build from Scratch", 0, "Source connectivity and validation rules"),
            ("Semantic layer and KPI definitions", "Backend Development", "Reuse Existing Module", 20, "Business glossary and source mappings"),
            ("Dashboards and executive views", "Frontend Development", "Reuse Existing Module", 30, "Visualization library and design system"),
            ("Forecasting or AI assistant layer", "Data Engineering", "Build from Scratch", 0, "Model selection, prompts, or feature pipelines"),
            ("Access control and auditability", "Backend Development", "Reuse Existing Module", 20, "RBAC, logging, and approval flows"),
        ],
        "additional_teams": ["Data Engineering", "Security / Compliance", "Business Analyst"],
    },
    {
        "id": "crm_platform",
        "name": "CRM and customer operations platform",
        "keywords": [
            "crm",
            "lead",
            "sales",
            "customer",
            "pipeline",
            "account",
            "opportunity",
            "portal",
        ],
        "products": [
            {
                "Product Name": "Salesforce Sales Cloud",
                "Organization": "Salesforce",
                "Key differentiators": "Mature CRM workflows, automation, and ecosystem breadth.",
            },
            {
                "Product Name": "HubSpot CRM",
                "Organization": "HubSpot",
                "Key differentiators": "Faster adoption with marketing and sales alignment.",
            },
            {
                "Product Name": "Zoho CRM",
                "Organization": "Zoho",
                "Key differentiators": "Cost-efficient CRM with flexible workflow automation.",
            },
        ],
        "modules": [
            ("Lead capture and enrichment", "Frontend Development", "Reuse Existing Module", 20, "Forms, scoring, and source connectors"),
            ("Sales workflow automation", "Backend Development", "Build from Scratch", 0, "Approval paths and pipeline stages"),
            ("Customer workspace and activity timeline", "Frontend Development", "Build from Scratch", 0, "Entity model and role-based views"),
            ("Integration and reporting layer", "Data Engineering", "Reuse Existing Module", 25, "CRM source sync and BI model"),
            ("Notifications and customer alerts", "Backend Development", "Reuse Existing Module", 20, "Email or messaging triggers"),
        ],
        "additional_teams": ["Business Analyst", "Support / Operations"],
    },
    {
        "id": "hr_platform",
        "name": "People and workforce platform",
        "keywords": [
            "hr",
            "employee",
            "payroll",
            "leave",
            "attendance",
            "workforce",
            "talent",
            "recruit",
        ],
        "products": [
            {
                "Product Name": "Workday",
                "Organization": "Workday",
                "Key differentiators": "Enterprise-grade workforce planning and people operations.",
            },
            {
                "Product Name": "Darwinbox",
                "Organization": "Darwinbox",
                "Key differentiators": "Modern HR experience with Asia-focused operational depth.",
            },
            {
                "Product Name": "SAP SuccessFactors",
                "Organization": "SAP",
                "Key differentiators": "Large-enterprise HR processes and compliance coverage.",
            },
        ],
        "modules": [
            ("Employee profile and self-service", "Frontend Development", "Reuse Existing Module", 20, "Identity, policy, and profile schema"),
            ("Attendance and leave workflows", "Backend Development", "Build from Scratch", 0, "Approval matrix and policy rules"),
            ("Manager dashboard and analytics", "Data Engineering", "Reuse Existing Module", 25, "HR metrics and reporting model"),
            ("Notifications and lifecycle triggers", "Backend Development", "Reuse Existing Module", 20, "Email or chat integrations"),
            ("Access governance and audit history", "Security / Compliance", "Reuse Existing Module", 15, "Access controls and compliance logging"),
        ],
        "additional_teams": ["Business Analyst", "Security / Compliance", "Support / Operations"],
    },
]

CHENNAI_HOLIDAYS = {
    2025: {
        date(2025, 1, 1): "New Year's Day",
        date(2025, 1, 14): "Pongal",
        date(2025, 1, 15): "Thiruvalluvar Day",
        date(2025, 1, 16): "Uzhavar Thirunal",
        date(2025, 1, 26): "Republic Day",
        date(2025, 2, 11): "Thai Poosam",
        date(2025, 3, 30): "Telugu New Year's Day",
        date(2025, 3, 31): "Ramzan (Idul Fitr)",
        date(2025, 4, 10): "Mahaveer Jayanthi",
        date(2025, 4, 14): "Tamil New Year's Day / Dr. B. R. Ambedkar's Birthday",
        date(2025, 4, 18): "Good Friday",
        date(2025, 5, 1): "May Day",
        date(2025, 6, 7): "Bakrid (Idul Azha)",
        date(2025, 7, 6): "Muharram",
        date(2025, 8, 15): "Independence Day",
        date(2025, 8, 16): "Krishna Jayanthi",
        date(2025, 8, 27): "Vinayakar Chathurthi",
        date(2025, 9, 5): "Milad-un-Nabi",
        date(2025, 10, 1): "Ayutha Pooja",
        date(2025, 10, 2): "Vijaya Dasami / Gandhi Jayanthi",
        date(2025, 10, 20): "Deepavali",
        date(2025, 12, 25): "Christmas",
    },
    2026: {
        date(2026, 1, 1): "New Year's Day",
        date(2026, 1, 15): "Pongal",
        date(2026, 1, 16): "Thiruvalluvar Day",
        date(2026, 1, 17): "Uzhavar Thirunal",
        date(2026, 1, 26): "Republic Day",
        date(2026, 2, 1): "Thai Poosam",
        date(2026, 3, 19): "Telugu New Year's Day",
        date(2026, 3, 21): "Ramzan (Idul Fitr)",
        date(2026, 3, 31): "Mahaveer Jayanthi",
        date(2026, 4, 3): "Good Friday",
        date(2026, 4, 14): "Tamil New Year's Day / Dr. B. R. Ambedkar's Birthday",
        date(2026, 5, 1): "May Day",
        date(2026, 5, 28): "Bakrid (Idul Azha)",
        date(2026, 6, 26): "Muharram",
        date(2026, 8, 15): "Independence Day",
        date(2026, 8, 26): "Milad-un-Nabi",
        date(2026, 9, 4): "Krishna Jayanthi",
        date(2026, 9, 14): "Vinayakar Chathurthi",
        date(2026, 10, 2): "Gandhi Jayanthi",
        date(2026, 10, 19): "Ayutha Pooja",
        date(2026, 10, 20): "Vijaya Dasami",
        date(2026, 11, 8): "Deepavali",
        date(2026, 12, 25): "Christmas",
    },
}

FALLBACK_FIXED_HOLIDAYS = {
    (1, 1): "New Year's Day",
    (1, 26): "Republic Day",
    (5, 1): "May Day",
    (8, 15): "Independence Day",
    (10, 2): "Gandhi Jayanthi",
    (12, 25): "Christmas",
}


def slugify(value):
    cleaned = re.sub(r"[^a-z0-9]+", "_", str(value).strip().lower())
    cleaned = cleaned.strip("_")
    return cleaned or "task"


def normalize_date(value):
    if pd.isna(value):
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    return pd.to_datetime(value).date()


def is_workday(day_value, holiday_dates):
    return day_value.weekday() < 5 and day_value not in holiday_dates


def next_workday(day_value, holiday_dates):
    current = normalize_date(day_value)
    while not is_workday(current, holiday_dates):
        current += timedelta(days=1)
    return current


def add_working_days(start_day, working_days, holiday_dates):
    if working_days <= 0:
        return next_workday(start_day, holiday_dates)
    current = next_workday(start_day, holiday_dates)
    remaining = working_days - 1
    while remaining > 0:
        current += timedelta(days=1)
        if is_workday(current, holiday_dates):
            remaining -= 1
    return current


def working_day_index(start_day, target_day, holiday_dates):
    start_value = next_workday(start_day, holiday_dates)
    target_value = normalize_date(target_day)
    if target_value <= start_value:
        return 0
    index = 0
    current = start_value
    while current < target_value:
        current += timedelta(days=1)
        if is_workday(current, holiday_dates):
            index += 1
    return index


def parse_dependencies(raw_value):
    tokens = [token.strip() for token in str(raw_value).replace(";", ",").split(",")]
    return [token for token in tokens if token]


def get_holiday_map_for_year(year_value):
    if year_value in CHENNAI_HOLIDAYS:
        return CHENNAI_HOLIDAYS[year_value]
    return {date(year_value, month, day): name for (month, day), name in FALLBACK_FIXED_HOLIDAYS.items()}


def build_default_holiday_df(start_day, duration_days):
    end_hint = add_working_days(start_day, max(int(duration_days), 1), set())
    years = sorted({normalize_date(start_day).year, normalize_date(end_hint).year})
    records = []
    for year_value in years:
        for holiday_day, holiday_name in get_holiday_map_for_year(year_value).items():
            records.append({"Date": holiday_day, "Holiday": holiday_name})
    holiday_df = pd.DataFrame(records)
    if holiday_df.empty:
        holiday_df = pd.DataFrame(columns=["Date", "Holiday"])
    holiday_df["Date"] = pd.to_datetime(holiday_df["Date"]).dt.date
    holiday_df = holiday_df.sort_values("Date").drop_duplicates(subset=["Date"], keep="last").reset_index(drop=True)
    return holiday_df


def infer_profile(description):
    text = str(description or "").lower()
    ranked = []
    for profile in PROFILE_CATALOG:
        score = sum(1 for keyword in profile["keywords"] if keyword in text)
        ranked.append((score, profile))
    ranked.sort(key=lambda item: item[0], reverse=True)
    if ranked and ranked[0][0] > 0:
        return ranked[0][1]
    return PROFILE_CATALOG[0]


def infer_complexity(description, duration_days, module_count):
    text = str(description or "").lower()
    score = 0
    if duration_days >= 150:
        score += 3
    elif duration_days >= 90:
        score += 2
    elif duration_days >= 45:
        score += 1

    for keyword in [
        "integration",
        "api",
        "enterprise",
        "realtime",
        "real-time",
        "payment",
        "security",
        "compliance",
        "audit",
        "data",
        "ai",
        "analytics",
        "multi",
    ]:
        if keyword in text:
            score += 1

    if module_count >= 5:
        score += 1
    if module_count >= 7:
        score += 1

    if score >= 6:
        return "High"
    if score >= 3:
        return "Medium"
    return "Low"


def build_market_comparison_df(profile):
    return pd.DataFrame(profile["products"])


def build_default_team_df(profile, complexity):
    base_teams = [
        "UI/UX Design",
        "Frontend Development",
        "Backend Development",
        "DevOps",
        "QA/Testing",
        "Project Manager",
        "Product Manager",
    ]
    team_names = list(dict.fromkeys(base_teams + profile.get("additional_teams", [])))
    records = []
    for team_name in team_names:
        suggested = TEAM_BASELINES[team_name][complexity]
        records.append(
            {
                "Team": team_name,
                "Resources": suggested,
                "Skill Level": TEAM_DEFAULT_SKILL[team_name][complexity],
                "Allocation %": 100,
                "Suggested Resources": suggested,
                "Allocation Guidance": TEAM_GUIDANCE[team_name],
            }
        )
    return pd.DataFrame(records)


def build_default_module_df(profile, complexity):
    module_rows = []
    for module_name, team_name, build_strategy, reuse_reduction, dependency_note in profile["modules"]:
        module_rows.append(
            {
                "Module": module_name,
                "Team Responsible": team_name,
                "Build Strategy": build_strategy,
                "Reuse Reduction %": reuse_reduction,
                "Dependencies": dependency_note,
                "Complexity Fit": complexity,
            }
        )
    return pd.DataFrame(module_rows)


def merge_team_defaults(default_df, existing_df):
    if existing_df is None or existing_df.empty:
        return default_df.copy()

    existing_map = existing_df.set_index("Team").to_dict(orient="index")
    merged_rows = []
    for row in default_df.to_dict(orient="records"):
        current = existing_map.get(row["Team"], {})
        merged_rows.append(
            {
                **row,
                "Resources": int(current.get("Resources", row["Resources"])) if str(current.get("Resources", row["Resources"])).strip() else row["Resources"],
                "Skill Level": current.get("Skill Level", row["Skill Level"]),
                "Allocation %": current.get("Allocation %", row.get("Allocation %", 100)),
            }
        )
    for row in existing_df.to_dict(orient="records"):
        if row["Team"] not in set(default_df["Team"]):
            merged_rows.append(row)
    merged_df = pd.DataFrame(merged_rows)
    merged_df["Resources"] = pd.to_numeric(merged_df["Resources"], errors="coerce").fillna(1).clip(lower=1).astype(int)
    merged_df["Allocation %"] = pd.to_numeric(merged_df["Allocation %"], errors="coerce").fillna(100).clip(lower=20, upper=100).astype(int)
    merged_df["Suggested Resources"] = pd.to_numeric(merged_df["Suggested Resources"], errors="coerce").fillna(1).clip(lower=1).astype(int)
    merged_df["Skill Level"] = merged_df["Skill Level"].where(merged_df["Skill Level"].isin(SKILL_OPTIONS), "Mid")
    return merged_df.reset_index(drop=True)


def merge_module_defaults(default_df, existing_df):
    if existing_df is None or existing_df.empty:
        return default_df.copy()

    existing_map = existing_df.set_index("Module").to_dict(orient="index")
    merged_rows = []
    for row in default_df.to_dict(orient="records"):
        current = existing_map.get(row["Module"], {})
        merged_rows.append(
            {
                **row,
                "Team Responsible": current.get("Team Responsible", row["Team Responsible"]),
                "Build Strategy": current.get("Build Strategy", row["Build Strategy"]),
                "Reuse Reduction %": current.get("Reuse Reduction %", row["Reuse Reduction %"]),
                "Dependencies": current.get("Dependencies", row["Dependencies"]),
            }
        )
    for row in existing_df.to_dict(orient="records"):
        if row["Module"] not in set(default_df["Module"]):
            merged_rows.append(row)
    merged_df = pd.DataFrame(merged_rows)
    merged_df["Reuse Reduction %"] = pd.to_numeric(merged_df["Reuse Reduction %"], errors="coerce").fillna(0).clip(lower=0, upper=80).astype(int)
    merged_df["Build Strategy"] = merged_df["Build Strategy"].where(merged_df["Build Strategy"].isin(BUILD_OPTIONS), BUILD_OPTIONS[0])
    return merged_df.reset_index(drop=True)


def allocate_phase_budgets(total_days, complexity):
    ratios = {
        "Low": [0.16, 0.15, 0.36, 0.17, 0.07, 0.09],
        "Medium": [0.14, 0.15, 0.40, 0.16, 0.06, 0.09],
        "High": [0.12, 0.14, 0.44, 0.15, 0.06, 0.09],
    }[complexity]
    raw_values = [ratio * total_days for ratio in ratios]
    floors = [max(1, int(math.floor(value))) for value in raw_values]
    while sum(floors) < total_days:
        remainder_index = max(range(len(raw_values)), key=lambda idx: raw_values[idx] - floors[idx])
        floors[remainder_index] += 1
    while sum(floors) > total_days:
        reduce_index = max(range(len(floors)), key=lambda idx: floors[idx])
        if floors[reduce_index] > 1:
            floors[reduce_index] -= 1
        else:
            break
    return dict(zip(ROADMAP_PHASES, floors))


def split_budget(total_value, weights):
    if total_value <= 0:
        return [1 for _ in weights]
    base = [max(1, int(math.floor(total_value * weight))) for weight in weights]
    while sum(base) < total_value:
        idx = max(range(len(weights)), key=lambda index: weights[index] - base[index] / max(total_value, 1))
        base[idx] += 1
    while sum(base) > total_value:
        idx = max(range(len(base)), key=lambda index: base[index])
        if base[idx] > 1:
            base[idx] -= 1
        else:
            break
    return base


def generate_default_task_df(project_name, duration_days, complexity, team_df, module_df):
    budgets = allocate_phase_budgets(max(int(duration_days), 15), complexity)
    req_kickoff, req_backlog, req_arch = split_budget(budgets["Requirement Gathering"], [0.22, 0.46, 0.32])
    design_ux = max(2, round(budgets["Design"] * 0.78))
    design_tech = max(2, round(budgets["Design"] * 0.86))
    design_plan = max(1, round(budgets["Design"] * 0.34))
    devops_effort = max(2, round(budgets["Development"] * 0.24))
    test_plan, test_exec, test_uat = split_budget(budgets["Testing"], [0.26, 0.46, 0.28])
    deploy_release, deploy_handover = split_budget(budgets["Deployment"], [0.65, 0.35])

    task_rows = [
        {
            "Task Key": "REQ_DISCOVERY",
            "Phase": "Requirement Gathering",
            "Task Name": f"{project_name or 'Project'} kickoff and discovery alignment",
            "Team Responsible": "Project Manager",
            "Effort Days": req_kickoff,
            "Execution": "Sequential",
            "Build Strategy": "Build from Scratch",
            "Reuse Reduction %": 0,
            "Dependency": "",
            "Reuse Dependency": "Stakeholder interviews and operating model inputs",
        },
        {
            "Task Key": "REQ_BACKLOG",
            "Phase": "Requirement Gathering",
            "Task Name": "Requirements backlog, personas, and acceptance criteria",
            "Team Responsible": "Product Manager",
            "Effort Days": req_backlog,
            "Execution": "Sequential",
            "Build Strategy": "Build from Scratch",
            "Reuse Reduction %": 0,
            "Dependency": "REQ_DISCOVERY",
            "Reuse Dependency": "Business workflows and prioritization rules",
        },
        {
            "Task Key": "REQ_ARCH",
            "Phase": "Requirement Gathering",
            "Task Name": "Solution architecture and delivery plan",
            "Team Responsible": "Backend Development",
            "Effort Days": req_arch,
            "Execution": "Sequential",
            "Build Strategy": "Build from Scratch",
            "Reuse Reduction %": 0,
            "Dependency": "REQ_BACKLOG",
            "Reuse Dependency": "Integration inventory and non-functional requirements",
        },
        {
            "Task Key": "DESIGN_UX",
            "Phase": "Design",
            "Task Name": "Experience flows, wireframes, and design system setup",
            "Team Responsible": "UI/UX Design",
            "Effort Days": design_ux,
            "Execution": "Parallel",
            "Build Strategy": "Build from Scratch",
            "Reuse Reduction %": 0,
            "Dependency": "REQ_BACKLOG",
            "Reuse Dependency": "Prioritized user journeys and brand guidance",
        },
        {
            "Task Key": "DESIGN_TECH",
            "Phase": "Design",
            "Task Name": "Technical design, APIs, and data contracts",
            "Team Responsible": "Backend Development",
            "Effort Days": design_tech,
            "Execution": "Parallel",
            "Build Strategy": "Build from Scratch",
            "Reuse Reduction %": 0,
            "Dependency": "REQ_ARCH",
            "Reuse Dependency": "Architecture decisions and interface mapping",
        },
        {
            "Task Key": "DESIGN_PLAN",
            "Phase": "Design",
            "Task Name": "Sprint plan, milestones, and dependency review",
            "Team Responsible": "Project Manager",
            "Effort Days": design_plan,
            "Execution": "Sequential",
            "Build Strategy": "Reuse Existing Module",
            "Reuse Reduction %": 15,
            "Dependency": "REQ_BACKLOG, REQ_ARCH",
            "Reuse Dependency": "Existing planning templates and delivery governance",
        },
        {
            "Task Key": "DEVOPS_BASELINE",
            "Phase": "Development",
            "Task Name": "Environment setup, CI/CD, and release controls",
            "Team Responsible": "DevOps",
            "Effort Days": devops_effort,
            "Execution": "Parallel",
            "Build Strategy": "Reuse Existing Module",
            "Reuse Reduction %": 20,
            "Dependency": "REQ_DISCOVERY",
            "Reuse Dependency": "Pipeline templates, IaC modules, and monitoring standards",
        },
    ]

    dev_budget = budgets["Development"]
    module_rows = module_df.to_dict(orient="records") if not module_df.empty else []
    if module_rows:
        weight_values = [1.15 - (index * 0.07) for index in range(len(module_rows))]
        weight_values = [max(0.72, value) for value in weight_values]
        for index, module_row in enumerate(module_rows):
            module_slug = slugify(module_row["Module"])
            module_effort = max(4, round(dev_budget * max(0.4, weight_values[index])))
            task_rows.append(
                {
                    "Task Key": f"DEV_{module_slug.upper()}",
                    "Phase": "Development",
                    "Task Name": module_row["Module"],
                    "Team Responsible": module_row["Team Responsible"],
                    "Effort Days": module_effort,
                    "Execution": "Parallel",
                    "Build Strategy": module_row["Build Strategy"],
                    "Reuse Reduction %": module_row["Reuse Reduction %"],
                    "Dependency": "DESIGN_UX, DESIGN_TECH, DEVOPS_BASELINE",
                    "Reuse Dependency": module_row["Dependencies"],
                }
            )

    if "Security / Compliance" in set(team_df["Team"]):
        task_rows.append(
            {
                "Task Key": "TEST_SECURITY",
                "Phase": "Testing",
                "Task Name": "Security and compliance validation",
                "Team Responsible": "Security / Compliance",
                "Effort Days": max(2, round(budgets["Testing"] * 0.32)),
                "Execution": "Parallel",
                "Build Strategy": "Build from Scratch",
                "Reuse Reduction %": 0,
                "Dependency": ", ".join(
                    [row["Task Key"] for row in task_rows if row["Phase"] == "Development" and row["Task Key"] != "DEVOPS_BASELINE"]
                ),
                "Reuse Dependency": "Security checklist, audit controls, and evidence pack",
            }
        )

    task_rows.extend(
        [
            {
                "Task Key": "TEST_PLAN",
                "Phase": "Testing",
                "Task Name": "Test planning, automation coverage, and traceability",
                "Team Responsible": "QA/Testing",
                "Effort Days": test_plan,
                "Execution": "Parallel",
                "Build Strategy": "Reuse Existing Module",
                "Reuse Reduction %": 15,
                "Dependency": "DESIGN_PLAN",
                "Reuse Dependency": "Existing test accelerators and regression suites",
            },
            {
                "Task Key": "TEST_EXECUTION",
                "Phase": "Testing",
                "Task Name": "System, integration, and defect validation",
                "Team Responsible": "QA/Testing",
                "Effort Days": test_exec,
                "Execution": "Sequential",
                "Build Strategy": "Build from Scratch",
                "Reuse Reduction %": 0,
                "Dependency": ", ".join(
                    ["TEST_PLAN"]
                    + [row["Task Key"] for row in task_rows if row["Phase"] == "Development" and row["Task Key"] != "DEVOPS_BASELINE"]
                ),
                "Reuse Dependency": "Stable build, test data, and environment readiness",
            },
            {
                "Task Key": "TEST_UAT",
                "Phase": "Testing",
                "Task Name": "Business UAT, sign-off, and release decision",
                "Team Responsible": "Product Manager",
                "Effort Days": test_uat,
                "Execution": "Sequential",
                "Build Strategy": "Build from Scratch",
                "Reuse Reduction %": 0,
                "Dependency": "TEST_EXECUTION",
                "Reuse Dependency": "Resolved defects and UAT script coverage",
            },
            {
                "Task Key": "DEPLOY_RELEASE",
                "Phase": "Deployment",
                "Task Name": "Release readiness, cutover, and production deployment",
                "Team Responsible": "DevOps",
                "Effort Days": deploy_release,
                "Execution": "Sequential",
                "Build Strategy": "Reuse Existing Module",
                "Reuse Reduction %": 20,
                "Dependency": "TEST_UAT",
                "Reuse Dependency": "Release checklist, change approvals, and rollback plan",
            },
            {
                "Task Key": "DEPLOY_HANDOVER",
                "Phase": "Deployment",
                "Task Name": "Operational handover, training, and business communications",
                "Team Responsible": "Project Manager",
                "Effort Days": deploy_handover,
                "Execution": "Sequential",
                "Build Strategy": "Reuse Existing Module",
                "Reuse Reduction %": 20,
                "Dependency": "DEPLOY_RELEASE",
                "Reuse Dependency": "Runbooks, user guides, and release notes",
            },
            {
                "Task Key": "SUPPORT_HYPERCARE",
                "Phase": "Post-Production Support",
                "Task Name": "Hypercare, adoption tracking, and KPI stabilization",
                "Team Responsible": "Support / Operations" if "Support / Operations" in set(team_df["Team"]) else "Project Manager",
                "Effort Days": max(3, budgets["Post-Production Support"]),
                "Execution": "Sequential",
                "Build Strategy": "Reuse Existing Module",
                "Reuse Reduction %": 10,
                "Dependency": "DEPLOY_HANDOVER",
                "Reuse Dependency": "Support rota, monitoring alerts, and incident workflow",
            },
        ]
    )

    task_df = pd.DataFrame(task_rows)
    task_df["Effort Days"] = pd.to_numeric(task_df["Effort Days"], errors="coerce").fillna(1).clip(lower=1).astype(int)
    return task_df


def ensure_unique_task_keys(task_df):
    seen = {}
    cleaned_rows = []
    for row in task_df.to_dict(orient="records"):
        raw_key = row.get("Task Key") or row.get("Task Name") or "TASK"
        base_key = slugify(raw_key).upper()
        seen[base_key] = seen.get(base_key, 0) + 1
        row["Task Key"] = base_key if seen[base_key] == 1 else f"{base_key}_{seen[base_key]}"
        cleaned_rows.append(row)
    return pd.DataFrame(cleaned_rows)


def merge_task_defaults(default_df, existing_df):
    default_df = ensure_unique_task_keys(default_df)
    if existing_df is None or existing_df.empty:
        return default_df.copy()

    existing_df = ensure_unique_task_keys(existing_df)
    existing_map = existing_df.set_index("Task Key").to_dict(orient="index")
    preserved_columns = {
        "Task Name",
        "Team Responsible",
        "Effort Days",
        "Execution",
        "Build Strategy",
        "Reuse Reduction %",
        "Dependency",
        "Reuse Dependency",
        "Phase",
    }
    merged_rows = []
    default_keys = set(default_df["Task Key"])
    for row in default_df.to_dict(orient="records"):
        current = existing_map.get(row["Task Key"], {})
        for column in preserved_columns:
            if column in current and str(current.get(column, "")).strip():
                row[column] = current[column]
        merged_rows.append(row)

    for row in existing_df.to_dict(orient="records"):
        if row["Task Key"] not in default_keys:
            merged_rows.append(row)

    merged_df = pd.DataFrame(merged_rows)
    merged_df["Effort Days"] = pd.to_numeric(merged_df["Effort Days"], errors="coerce").fillna(1).clip(lower=1).astype(int)
    merged_df["Reuse Reduction %"] = pd.to_numeric(merged_df["Reuse Reduction %"], errors="coerce").fillna(0).clip(lower=0, upper=80).astype(int)
    merged_df["Execution"] = merged_df["Execution"].where(merged_df["Execution"].isin(EXECUTION_OPTIONS), "Sequential")
    merged_df["Build Strategy"] = merged_df["Build Strategy"].where(merged_df["Build Strategy"].isin(BUILD_OPTIONS), BUILD_OPTIONS[0])
    merged_df["Phase"] = merged_df["Phase"].where(merged_df["Phase"].isin(ROADMAP_PHASES), "Development")
    return ensure_unique_task_keys(merged_df.reset_index(drop=True))


def clean_holiday_df(holiday_df):
    if holiday_df is None or holiday_df.empty:
        return pd.DataFrame(columns=["Date", "Holiday"])
    clean_df = holiday_df.copy()
    clean_df = clean_df.dropna(subset=["Date"])
    clean_df["Date"] = pd.to_datetime(clean_df["Date"]).dt.date
    clean_df["Holiday"] = clean_df["Holiday"].fillna("Project Holiday").astype(str)
    clean_df = clean_df.sort_values("Date").drop_duplicates(subset=["Date"], keep="last").reset_index(drop=True)
    return clean_df


def clean_team_df(team_df):
    clean_df = team_df.copy()
    clean_df["Team"] = clean_df["Team"].fillna("Custom Team").astype(str).str.strip()
    clean_df = clean_df[clean_df["Team"] != ""]
    clean_df["Resources"] = pd.to_numeric(clean_df["Resources"], errors="coerce").fillna(1).clip(lower=1).astype(int)
    clean_df["Allocation %"] = pd.to_numeric(clean_df["Allocation %"], errors="coerce").fillna(100).clip(lower=20, upper=100).astype(int)
    clean_df["Suggested Resources"] = pd.to_numeric(clean_df["Suggested Resources"], errors="coerce").fillna(clean_df["Resources"]).clip(lower=1).astype(int)
    clean_df["Skill Level"] = clean_df["Skill Level"].where(clean_df["Skill Level"].isin(SKILL_OPTIONS), "Mid")
    clean_df["Allocation Guidance"] = clean_df["Allocation Guidance"].fillna("").astype(str)
    return clean_df.drop_duplicates(subset=["Team"], keep="last").reset_index(drop=True)


def clean_module_df(module_df):
    clean_df = module_df.copy()
    clean_df["Module"] = clean_df["Module"].fillna("Custom Module").astype(str).str.strip()
    clean_df = clean_df[clean_df["Module"] != ""]
    clean_df["Reuse Reduction %"] = pd.to_numeric(clean_df["Reuse Reduction %"], errors="coerce").fillna(0).clip(lower=0, upper=80).astype(int)
    clean_df["Build Strategy"] = clean_df["Build Strategy"].where(clean_df["Build Strategy"].isin(BUILD_OPTIONS), BUILD_OPTIONS[0])
    clean_df["Dependencies"] = clean_df["Dependencies"].fillna("").astype(str)
    clean_df["Complexity Fit"] = clean_df["Complexity Fit"].fillna("Medium").astype(str)
    return clean_df.drop_duplicates(subset=["Module"], keep="last").reset_index(drop=True)


def clean_task_df(task_df):
    clean_df = task_df.copy()
    clean_df["Task Key"] = clean_df["Task Key"].fillna("").astype(str)
    clean_df["Task Name"] = clean_df["Task Name"].fillna("Untitled Task").astype(str)
    clean_df["Phase"] = clean_df["Phase"].where(clean_df["Phase"].isin(ROADMAP_PHASES), "Development")
    clean_df["Team Responsible"] = clean_df["Team Responsible"].fillna("Project Manager").astype(str)
    clean_df["Effort Days"] = pd.to_numeric(clean_df["Effort Days"], errors="coerce").fillna(1).clip(lower=1).astype(int)
    clean_df["Execution"] = clean_df["Execution"].where(clean_df["Execution"].isin(EXECUTION_OPTIONS), "Sequential")
    clean_df["Build Strategy"] = clean_df["Build Strategy"].where(clean_df["Build Strategy"].isin(BUILD_OPTIONS), BUILD_OPTIONS[0])
    clean_df["Reuse Reduction %"] = pd.to_numeric(clean_df["Reuse Reduction %"], errors="coerce").fillna(0).clip(lower=0, upper=80).astype(int)
    clean_df["Dependency"] = clean_df["Dependency"].fillna("").astype(str)
    clean_df["Reuse Dependency"] = clean_df["Reuse Dependency"].fillna("").astype(str)
    clean_df = clean_df[clean_df["Task Name"].str.strip() != ""]
    return ensure_unique_task_keys(clean_df.reset_index(drop=True))


def compute_adjusted_duration(task_row, team_df):
    team_lookup = team_df.set_index("Team").to_dict(orient="index")
    team_name = task_row["Team Responsible"]
    team_settings = team_lookup.get(team_name, {"Resources": 1, "Suggested Resources": 1, "Skill Level": "Mid", "Allocation %": 100})
    resources = max(int(team_settings.get("Resources", 1)), 1)
    suggested = max(int(team_settings.get("Suggested Resources", resources)), 1)
    allocation_pct = max(int(team_settings.get("Allocation %", 100)), 20)
    skill_level = team_settings.get("Skill Level", "Mid")
    effective_capacity = max(resources * (allocation_pct / 100.0), 0.4)
    resource_factor = min(1.85, max(0.62, suggested / effective_capacity))
    skill_factor = SKILL_FACTOR.get(skill_level, 1.0)
    if task_row["Build Strategy"] == "Reuse Existing Module":
        reuse_factor = max(0.35, 1 - (float(task_row["Reuse Reduction %"]) / 100.0))
    else:
        reuse_factor = 1.0
    adjusted = max(1, int(math.ceil(float(task_row["Effort Days"]) * resource_factor * skill_factor * reuse_factor)))
    return adjusted


def schedule_tasks(task_df, team_df, start_day, holiday_df):
    holiday_dates = set(clean_holiday_df(holiday_df)["Date"].tolist())
    working_start = next_workday(start_day, holiday_dates)
    task_df = clean_task_df(task_df)
    team_df = clean_team_df(team_df)
    team_capacity = {
        row["Team"]: max(1, int(math.floor(max(int(row["Resources"]), 1) * (int(row["Allocation %"]) / 100.0))))
        for row in team_df.to_dict(orient="records")
    }

    tasks = {}
    for position, row in enumerate(task_df.to_dict(orient="records")):
        dependencies = [dep for dep in parse_dependencies(row["Dependency"]) if dep]
        tasks[row["Task Key"]] = {
            **row,
            "Dependencies": dependencies,
            "Adjusted Duration": compute_adjusted_duration(row, team_df),
            "Priority": position,
        }

    completed = {}
    active = []
    schedule = {}
    current_day = working_start
    guard = 0

    while len(completed) < len(tasks) and guard < 4000:
        guard += 1
        if not is_workday(current_day, holiday_dates):
            current_day += timedelta(days=1)
            continue

        active_by_team = {}
        for active_task in active:
            active_by_team.setdefault(active_task["Team Responsible"], 0)
            active_by_team[active_task["Team Responsible"]] += 1

        ready_tasks = []
        for task_key, task in tasks.items():
            if task_key in schedule:
                continue
            if any(dep not in completed for dep in task["Dependencies"]):
                continue
            ready_tasks.append(task)

        ready_tasks.sort(
            key=lambda item: (
                PHASE_ORDER.get(item["Phase"], 99),
                0 if item["Execution"] == "Sequential" else 1,
                -len(item["Dependencies"]),
                item["Priority"],
            )
        )

        for task in ready_tasks:
            team_name = task["Team Responsible"]
            capacity = team_capacity.get(team_name, 1)
            active_count = active_by_team.get(team_name, 0)
            if active_count >= capacity:
                continue
            active.append(
                {
                    **task,
                    "Start Date": current_day,
                    "Remaining": task["Adjusted Duration"],
                }
            )
            schedule[task["Task Key"]] = {"Start Date": current_day}
            active_by_team[team_name] = active_count + 1

        next_active = []
        for active_task in active:
            active_task["Remaining"] -= 1
            if active_task["Remaining"] <= 0:
                completed[active_task["Task Key"]] = current_day
                schedule[active_task["Task Key"]]["End Date"] = current_day
            else:
                next_active.append(active_task)
        active = next_active
        current_day += timedelta(days=1)

    if len(completed) < len(tasks):
        raise RuntimeError("Roadmap scheduler could not resolve all tasks. Check task dependencies for loops.")

    roadmap_rows = []
    for task_key, task in tasks.items():
        start_value = schedule[task_key]["Start Date"]
        end_value = schedule[task_key]["End Date"]
        roadmap_rows.append(
            {
                "Task Key": task_key,
                "Phase": task["Phase"],
                "Task Name": task["Task Name"],
                "Team Responsible": task["Team Responsible"],
                "Execution": task["Execution"],
                "Build Strategy": task["Build Strategy"],
                "Reuse Reduction %": task["Reuse Reduction %"],
                "Dependency": ", ".join(task["Dependencies"]),
                "Dependency Notes": task["Reuse Dependency"],
                "Start Date": start_value,
                "End Date": end_value,
                "Duration": task["Adjusted Duration"],
                "Status": "Planned",
            }
        )

    roadmap_df = pd.DataFrame(roadmap_rows)
    roadmap_df["Start Date"] = pd.to_datetime(roadmap_df["Start Date"]).dt.date
    roadmap_df["End Date"] = pd.to_datetime(roadmap_df["End Date"]).dt.date
    roadmap_df = roadmap_df.sort_values(
        by=["Start Date", "End Date", "Phase", "Task Name"],
        key=lambda series: series.map(PHASE_ORDER) if series.name == "Phase" else series,
    ).reset_index(drop=True)
    return roadmap_df, holiday_dates, working_start


def compute_critical_path(task_df):
    task_df = clean_task_df(task_df)
    tasks = {row["Task Key"]: row for row in task_df.to_dict(orient="records")}
    memo = {}

    def walk(task_key):
        if task_key in memo:
            return memo[task_key]
        task = tasks[task_key]
        current_duration = max(1, int(task["Effort Days"]))
        dependencies = [dep for dep in parse_dependencies(task["Dependency"]) if dep in tasks]
        if not dependencies:
            memo[task_key] = (current_duration, [task_key])
            return memo[task_key]
        best_duration = -1
        best_path = []
        for dependency in dependencies:
            dep_duration, dep_path = walk(dependency)
            if dep_duration > best_duration:
                best_duration = dep_duration
                best_path = dep_path
        memo[task_key] = (best_duration + current_duration, best_path + [task_key])
        return memo[task_key]

    longest_duration = -1
    longest_path = []
    for task_key in tasks:
        duration_value, path = walk(task_key)
        if duration_value > longest_duration:
            longest_duration = duration_value
            longest_path = path
    return longest_path


def build_team_utilization(roadmap_df, team_df, start_day, end_day, holiday_dates):
    schedule_days = max(1, working_day_index(start_day, end_day, holiday_dates) + 1)
    resource_lookup = clean_team_df(team_df).set_index("Team").to_dict(orient="index")
    rows = []
    for team_name, group_df in roadmap_df.groupby("Team Responsible"):
        resources = max(int(resource_lookup.get(team_name, {}).get("Resources", 1)), 1)
        allocation_pct = max(int(resource_lookup.get(team_name, {}).get("Allocation %", 100)), 20)
        effective_capacity = max(resources * (allocation_pct / 100.0), 0.4)
        assigned_task_days = int(group_df["Duration"].sum())
        utilization = assigned_task_days / max(effective_capacity * schedule_days, 1)
        idle_capacity_days = max((effective_capacity * schedule_days) - assigned_task_days, 0)
        rows.append(
            {
                "Team": team_name,
                "Resources": resources,
                "Allocation %": allocation_pct,
                "Effective Capacity": round(effective_capacity, 1),
                "Assigned Task Days": assigned_task_days,
                "Utilization": utilization,
                "Idle Capacity Days": round(idle_capacity_days, 1),
            }
        )
    utilization_df = pd.DataFrame(rows)
    if utilization_df.empty:
        utilization_df = pd.DataFrame(columns=["Team", "Resources", "Allocation %", "Effective Capacity", "Assigned Task Days", "Utilization", "Idle Capacity Days"])
    utilization_df = utilization_df.sort_values("Utilization", ascending=False).reset_index(drop=True)
    return utilization_df


def attach_risk_levels(roadmap_df, task_df, team_df, critical_path):
    task_lookup = clean_task_df(task_df).set_index("Task Key").to_dict(orient="index")
    team_lookup = clean_team_df(team_df).set_index("Team").to_dict(orient="index")
    roadmap_rows = []
    for row in roadmap_df.to_dict(orient="records"):
        source = task_lookup.get(row["Task Key"], {})
        team_name = row["Team Responsible"]
        team_settings = team_lookup.get(team_name, {"Resources": 1, "Suggested Resources": 1, "Skill Level": "Mid"})
        score = 0
        dependencies = parse_dependencies(source.get("Dependency", ""))
        if row["Task Key"] in critical_path:
            score += 2
        if row["Duration"] >= max(5, roadmap_df["Duration"].median()):
            score += 1
        if len(dependencies) >= 2:
            score += 1
        if source.get("Build Strategy") == "Build from Scratch" and row["Phase"] == "Development":
            score += 1
        if team_settings.get("Skill Level") == "Junior":
            score += 1
        if int(team_settings.get("Resources", 1)) < int(team_settings.get("Suggested Resources", 1)):
            score += 1
        if score >= 4:
            risk_level = "High"
        elif score >= 2:
            risk_level = "Medium"
        else:
            risk_level = "Low"
        row["Risk"] = risk_level
        row["Critical Path"] = "Yes" if row["Task Key"] in critical_path else "No"
        roadmap_rows.append(row)
    risk_df = pd.DataFrame(roadmap_rows)
    risk_df["Risk Sort"] = risk_df["Risk"].map(RISK_PRIORITY)
    return risk_df


def build_gantt_figure(roadmap_df):
    gantt_df = roadmap_df.copy()
    gantt_df["Task Label"] = gantt_df["Task Name"]
    fig = px.timeline(
        gantt_df,
        x_start="Start Date",
        x_end="End Date",
        y="Task Label",
        color="Phase",
        hover_data={
            "Team Responsible": True,
            "Duration": True,
            "Dependency": True,
            "Risk": True,
            "Task Label": False,
            "Start Date": True,
            "End Date": True,
        },
        category_orders={"Phase": ROADMAP_PHASES},
    )
    fig.update_yaxes(autorange="reversed")
    fig.update_layout(
        margin=dict(t=28, l=10, r=10, b=10),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Manrope, Segoe UI, sans-serif", color="#334155"),
        legend=dict(orientation="h", y=1.08, x=0),
        xaxis_title="Timeline",
        yaxis_title="Task",
    )
    return fig


def build_roadmap_pdf(project_name, project_description, project_summary_df, market_df, timeline_df, roadmap_df, recommendations):
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=12)
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 16)
    pdf.cell(0, 10, project_name or "Enterprise Project Roadmap", ln=True)
    pdf.set_font("Helvetica", "", 10)
    pdf.multi_cell(0, 6, project_description or "Project roadmap export")
    pdf.ln(2)

    def add_section(title, rows):
        pdf.set_font("Helvetica", "B", 12)
        pdf.cell(0, 8, title, ln=True)
        pdf.set_font("Helvetica", "", 9)
        for label, value in rows:
            pdf.multi_cell(0, 5, f"{label}: {value}")
        pdf.ln(1)

    add_section("Project Summary", [(row["Attribute"], row["Value"]) for row in project_summary_df.to_dict(orient="records")])
    add_section("Timeline Summary", [(row["Metric"], row["Value"]) for row in timeline_df.to_dict(orient="records")])

    market_rows = []
    for row in market_df.head(4).to_dict(orient="records"):
        market_rows.append((row["Product Name"], f"{row['Organization']} | {row['Key differentiators']}"))
    add_section("Market Comparison", market_rows)

    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(0, 8, "Top Roadmap Tasks", ln=True)
    pdf.set_font("Helvetica", "", 9)
    for row in roadmap_df.head(12).to_dict(orient="records"):
        pdf.multi_cell(
            0,
            5,
            f"{row['Task Name']} | {row['Team Responsible']} | {row['Start Date'].strftime('%d %b %Y')} -> {row['End Date'].strftime('%d %b %Y')} | Risk: {row['Risk']}",
        )
    pdf.ln(1)

    add_section("Recommendations", [(f"Action {index + 1}", item) for index, item in enumerate(recommendations[:8])])
    return pdf.output(dest="S").encode("latin-1", errors="replace")


def build_gantt_text(roadmap_df, start_day, holiday_dates):
    if roadmap_df.empty:
        return "No roadmap tasks generated yet."

    total_working_span = max(1, working_day_index(start_day, roadmap_df["End Date"].max(), holiday_dates) + 1)
    scale = max(1, math.ceil(total_working_span / 48))
    header_units = math.ceil(total_working_span / scale)
    header = " " * 33 + "".join(f"{unit + 1:>2}" for unit in range(header_units))
    legend = f"Scale: 1 block = {scale} working day(s)"
    lines = [legend, header]

    for row in roadmap_df.sort_values(["Start Date", "Phase", "Task Name"]).to_dict(orient="records"):
        start_offset = working_day_index(start_day, row["Start Date"], holiday_dates)
        start_slot = start_offset // scale
        duration_slots = max(1, math.ceil(int(row["Duration"]) / scale))
        bar = "  " * start_slot + "[]" * duration_slots
        line = f"{row['Task Name'][:30]:30} {bar} {row['Start Date'].strftime('%d %b')} -> {row['End Date'].strftime('%d %b')}"
        lines.append(line)

    return "\n".join(lines)


def build_recommendations(roadmap_df, utilization_df, critical_path, complexity, target_end, actual_end, team_df):
    recommendations = []
    schedule_slip = working_day_index(target_end, actual_end, set()) if actual_end > target_end else 0
    if actual_end > target_end:
        recommendations.append(
            f"Timeline is slipping by approximately {schedule_slip} working day(s); add capacity to the longest-path teams or simplify build-scratch modules."
        )
    hot_teams = utilization_df[utilization_df["Utilization"] >= 0.85]
    for row in hot_teams.head(3).to_dict(orient="records"):
        recommendations.append(
            f"{row['Team']} is highly utilized at about {row['Utilization'] * 100:.0f}% of planned capacity; consider one more resource or reduce concurrent scope."
        )
    if any(task_key.startswith("DEV_") for task_key in critical_path):
        recommendations.append("Critical path runs through development modules; lock reuse decisions early to avoid downstream test compression.")
    if "Security / Compliance" not in set(clean_team_df(team_df)["Team"]) and complexity == "High":
        recommendations.append("Add Security / Compliance ownership for enterprise-grade validation before deployment.")
    if not recommendations:
        recommendations.append("Current plan is balanced for the selected scope; keep weekly review checkpoints and protect design freeze dates.")
    return recommendations


def build_export_workbook(project_summary_df, market_df, timeline_df, team_df, module_df, task_df, roadmap_df, risk_df, holiday_df, gantt_text):
    output = BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        project_summary_df.to_excel(writer, index=False, sheet_name="Project Summary")
        market_df.to_excel(writer, index=False, sheet_name="Market Comparison")
        timeline_df.to_excel(writer, index=False, sheet_name="Timeline Summary")
        team_df.to_excel(writer, index=False, sheet_name="Team Allocation")
        module_df.to_excel(writer, index=False, sheet_name="Module Strategy")
        task_df.to_excel(writer, index=False, sheet_name="Task Breakdown")
        roadmap_df.to_excel(writer, index=False, sheet_name="Roadmap")
        risk_df.to_excel(writer, index=False, sheet_name="Risk Register")
        holiday_df.to_excel(writer, index=False, sheet_name="Holiday Calendar")
        pd.DataFrame({"Gantt Timeline": gantt_text.splitlines()}).to_excel(writer, index=False, sheet_name="Gantt View")
    output.seek(0)
    return output.getvalue()


def render_roadmap_workspace():
    st.markdown(
        """
        <style>
        .roadmap-section-title {
            margin: 0 0 0.35rem 0;
            color: #0f172a;
            font-size: 1.1rem;
            font-weight: 800;
        }
        .roadmap-section-copy {
            margin: 0 0 0.9rem 0;
            color: #475569;
            font-size: 0.92rem;
            line-height: 1.55;
        }
        .roadmap-pill {
            display: inline-flex;
            align-items: center;
            padding: 6px 10px;
            margin: 0 8px 8px 0;
            border-radius: 999px;
            background: rgba(37, 99, 235, 0.10);
            border: 1px solid rgba(37, 99, 235, 0.14);
            color: #173ea5;
            font-size: 0.78rem;
            font-weight: 700;
        }
        .roadmap-metric-card {
            background: linear-gradient(180deg, rgba(255,255,255,0.95) 0%, rgba(241,246,255,0.98) 100%);
            border: 1px solid rgba(148, 163, 184, 0.18);
            border-radius: 20px;
            padding: 18px 20px;
            box-shadow: 0 18px 40px rgba(15, 23, 42, 0.08);
            min-height: 138px;
        }
        .roadmap-metric-label {
            color: #64748b;
            text-transform: uppercase;
            letter-spacing: 0.08em;
            font-size: 0.74rem;
            font-weight: 800;
        }
        .roadmap-metric-value {
            color: #0f172a;
            font-size: 1.8rem;
            font-weight: 800;
            margin-top: 10px;
        }
        .roadmap-metric-note {
            color: #475569;
            font-size: 0.92rem;
            line-height: 1.5;
            margin-top: 8px;
        }
        .roadmap-risk-pill {
            display: inline-flex;
            align-items: center;
            padding: 6px 10px;
            border-radius: 999px;
            font-size: 0.78rem;
            font-weight: 800;
            margin-right: 8px;
        }
        .risk-high {
            background: rgba(220, 38, 38, 0.14);
            color: #b91c1c;
        }
        .risk-medium {
            background: rgba(217, 119, 6, 0.14);
            color: #b45309;
        }
        .risk-low {
            background: rgba(5, 150, 105, 0.14);
            color: #047857;
        }
        .gantt-shell {
            background: linear-gradient(180deg, rgba(12, 18, 34, 0.98) 0%, rgba(16, 36, 69, 0.98) 100%);
            border-radius: 18px;
            padding: 16px;
            border: 1px solid rgba(148, 163, 184, 0.14);
            box-shadow: 0 20px 38px rgba(15, 23, 42, 0.12);
        }
        .gantt-shell pre {
            margin: 0;
            white-space: pre-wrap;
            color: #e2e8f0;
            font-size: 0.78rem;
            line-height: 1.55;
            font-family: "SFMono-Regular", "Consolas", "Menlo", monospace;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    project_name = st.text_input("Project Name", value=st.session_state.get("roadmap_project_name", ""), key="roadmap_project_name")
    input_cols = st.columns([1.5, 1.1, 0.7], gap="small")
    with input_cols[0]:
        project_description = st.text_area(
            "Project Description",
            value=st.session_state.get(
                "roadmap_project_description",
                "Build an enterprise delivery workspace for portfolio planning, team allocation, workflow visibility, and executive reporting.",
            ),
            key="roadmap_project_description",
            height=130,
        )
    with input_cols[1]:
        duration_days = int(
            st.number_input(
                "Project Duration (working days)",
                min_value=10,
                max_value=365,
                value=int(st.session_state.get("roadmap_duration_days", 90)),
                step=5,
                key="roadmap_duration_days",
            )
        )
        start_day = normalize_date(
            st.date_input(
                "Project Start Date",
                value=st.session_state.get("roadmap_start_date", date.today()),
                key="roadmap_start_date",
            )
        )
    with input_cols[2]:
        st.markdown(
            """
            <div class="workspace-detail-card" style="padding:16px 18px;">
                <h4>Planning Notes</h4>
                <p>Roadmap dates exclude weekends plus the editable Chennai holiday calendar below. Resource counts, skill mix, and reuse choices will recalculate the plan automatically.</p>
            </div>
            """,
            unsafe_allow_html=True,
        )

    profile = infer_profile(project_description)
    default_module_df = build_default_module_df(profile, "Medium")
    complexity = infer_complexity(project_description, duration_days, len(default_module_df))
    default_team_df = build_default_team_df(profile, complexity)
    default_module_df = build_default_module_df(profile, complexity)
    default_holiday_df = build_default_holiday_df(start_day, duration_days)

    signature = "|".join(
        [
            project_name.strip(),
            project_description.strip(),
            str(duration_days),
            start_day.isoformat(),
            profile["id"],
            complexity,
        ]
    )

    if st.session_state.get("roadmap_signature") != signature:
        st.session_state["roadmap_signature"] = signature
        st.session_state["roadmap_team_df"] = merge_team_defaults(default_team_df, st.session_state.get("roadmap_team_df"))
        st.session_state["roadmap_module_df"] = merge_module_defaults(default_module_df, st.session_state.get("roadmap_module_df"))
        st.session_state["roadmap_holiday_df"] = clean_holiday_df(
            pd.concat(
                [default_holiday_df, st.session_state.get("roadmap_holiday_df", pd.DataFrame(columns=["Date", "Holiday"]))],
                ignore_index=True,
            )
        )
        generated_task_df = generate_default_task_df(
            project_name,
            duration_days,
            complexity,
            st.session_state["roadmap_team_df"],
            st.session_state["roadmap_module_df"],
        )
        st.session_state["roadmap_task_df"] = merge_task_defaults(generated_task_df, st.session_state.get("roadmap_task_df"))

    team_df = clean_team_df(st.session_state["roadmap_team_df"])
    module_df = clean_module_df(st.session_state["roadmap_module_df"])
    holiday_df = clean_holiday_df(st.session_state["roadmap_holiday_df"])

    generated_task_df = generate_default_task_df(project_name, duration_days, complexity, team_df, module_df)
    task_df = merge_task_defaults(generated_task_df, st.session_state["roadmap_task_df"])

    holiday_dates = set(holiday_df["Date"].tolist())
    planned_start = next_workday(start_day, holiday_dates)
    target_end = add_working_days(start_day, duration_days, holiday_dates)
    market_df = build_market_comparison_df(profile)

    st.markdown(
        f"""
        <div class="app-hero">
            <div class="hero-main">
                <div class="hero-kicker">Project Roadmap Studio</div>
                <div class="hero-title">{project_name or 'Enterprise Project Roadmap'}</div>
                <p class="hero-text">{project_description}</p>
                <div class="hero-meta">
                    <span class="hero-meta-chip">Profile: {profile['name']}</span>
                    <span class="hero-meta-chip">Complexity: {complexity}</span>
                    <span class="hero-meta-chip">Target duration: {duration_days} working days</span>
                    <span class="hero-meta-chip">Chennai calendar enabled</span>
                </div>
            </div>
            <div class="hero-panel">
                <span class="hero-panel-label">Planning Brief</span>
                <span class="hero-panel-title">{planned_start.strftime('%d %b %Y')}</span>
                <p class="hero-panel-copy">Working start date after weekends and configured Chennai holidays. The roadmap will adapt immediately as resource counts, task effort, and reuse choices change.</p>
                <div class="hero-panel-grid">
                    <div class="hero-panel-item">
                        <span class="hero-panel-value">{duration_days}</span>
                        <span class="hero-panel-caption">Working days</span>
                    </div>
                    <div class="hero-panel-item">
                        <span class="hero-panel-value">{len(module_df)}</span>
                        <span class="hero-panel-caption">Modules</span>
                    </div>
                    <div class="hero-panel-item">
                        <span class="hero-panel-value">{len(team_df)}</span>
                        <span class="hero-panel-caption">Teams</span>
                    </div>
                    <div class="hero-panel-item">
                        <span class="hero-panel-value">{target_end.strftime('%d %b')}</span>
                        <span class="hero-panel-caption">Target end</span>
                    </div>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown("### 1. Project Summary")
    summary_rows = [
        {"Attribute": "Project Name", "Value": project_name or "Untitled Project"},
        {"Attribute": "Product Profile", "Value": profile["name"]},
        {"Attribute": "Complexity", "Value": complexity},
        {"Attribute": "Planning Start Date", "Value": planned_start.strftime("%d %b %Y")},
        {"Attribute": "Target End Date", "Value": target_end.strftime("%d %b %Y")},
        {"Attribute": "Total Working Days", "Value": duration_days},
    ]
    project_summary_df = pd.DataFrame(summary_rows)
    st.dataframe(project_summary_df, use_container_width=True, hide_index=True)

    st.markdown("### 2. Market Comparison")
    st.markdown(
        "<div class='roadmap-section-copy'>Representative market references are inferred from the project description so the roadmap can be positioned against comparable enterprise products.</div>",
        unsafe_allow_html=True,
    )
    st.dataframe(market_df, use_container_width=True, hide_index=True)

    st.markdown("### 3. Timeline Summary")
    timeline_cols = st.columns(4, gap="small")
    timeline_cards = [
        ("Selected Start", start_day.strftime("%d %b %Y"), "User-selected calendar date for planning."),
        ("Working Start", planned_start.strftime("%d %b %Y"), "Automatically shifted if the chosen date is not a working day."),
        ("Target End", target_end.strftime("%d %b %Y"), "Calculated with weekends and Chennai holidays excluded."),
        ("Working Days", str(duration_days), "Baseline duration before resource-driven schedule changes."),
    ]
    for column, (label, value, note) in zip(timeline_cols, timeline_cards):
        column.markdown(
            f"""
            <div class="roadmap-metric-card">
                <div class="roadmap-metric-label">{label}</div>
                <div class="roadmap-metric-value">{value}</div>
                <div class="roadmap-metric-note">{note}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    editor_cols = st.columns([1.35, 0.95], gap="large")
    with editor_cols[0]:
        st.markdown("### 4. Team Allocation Table")
        st.markdown(
            "<div class='roadmap-section-copy'>Resource count and skill level are editable. Timeline and utilization will recalculate as soon as you change team capacity.</div>",
            unsafe_allow_html=True,
        )
        team_editor = st.data_editor(
            team_df,
            key="roadmap_team_editor",
            use_container_width=True,
            hide_index=True,
            num_rows="dynamic",
            column_config={
                "Team": st.column_config.TextColumn("Team", required=True),
                "Resources": st.column_config.NumberColumn("Resources", min_value=1, max_value=30, step=1),
                "Skill Level": st.column_config.SelectboxColumn("Skill Level", options=SKILL_OPTIONS, required=True),
                "Allocation %": st.column_config.NumberColumn("Allocation %", min_value=20, max_value=100, step=5),
                "Suggested Resources": st.column_config.NumberColumn("Suggested", disabled=True),
                "Allocation Guidance": st.column_config.TextColumn("Allocation Guidance", width="large"),
            },
        )
        team_df = clean_team_df(team_editor)
        st.session_state["roadmap_team_df"] = team_df

    with editor_cols[1]:
        st.markdown("### Holiday Calendar")
        st.markdown(
            "<div class='roadmap-section-copy'>Defaults are based on Chennai/Tamil Nadu public holidays. Add or remove dates to reflect project-specific shutdowns, client holidays, or release freezes.</div>",
            unsafe_allow_html=True,
        )
        holiday_editor = st.data_editor(
            holiday_df,
            key="roadmap_holiday_editor",
            use_container_width=True,
            hide_index=True,
            num_rows="dynamic",
            column_config={
                "Date": st.column_config.DateColumn("Date", format="DD-MM-YYYY", required=True),
                "Holiday": st.column_config.TextColumn("Holiday", required=True),
            },
        )
        holiday_df = clean_holiday_df(holiday_editor)
        st.session_state["roadmap_holiday_df"] = holiday_df

    module_df = merge_module_defaults(default_module_df, st.session_state.get("roadmap_module_df"))
    st.markdown("### 5. Development Approach Selection")
    st.markdown(
        "<div class='roadmap-section-copy'>Choose build versus reuse at the module level. Reuse reduction directly compresses the module timeline while the dependency note captures what must already exist.</div>",
        unsafe_allow_html=True,
    )
    module_editor = st.data_editor(
        module_df,
        key="roadmap_module_editor",
        use_container_width=True,
        hide_index=True,
        num_rows="dynamic",
        column_config={
            "Module": st.column_config.TextColumn("Module", required=True, width="medium"),
            "Team Responsible": st.column_config.SelectboxColumn("Team Responsible", options=sorted(team_df["Team"].tolist()), required=True),
            "Build Strategy": st.column_config.SelectboxColumn("Build Strategy", options=BUILD_OPTIONS, required=True),
            "Reuse Reduction %": st.column_config.NumberColumn("Reuse Reduction %", min_value=0, max_value=80, step=5),
            "Dependencies": st.column_config.TextColumn("Dependencies", width="large"),
            "Complexity Fit": st.column_config.TextColumn("Complexity Fit", disabled=True),
        },
    )
    module_df = clean_module_df(module_editor)
    st.session_state["roadmap_module_df"] = module_df

    regenerated_task_df = generate_default_task_df(project_name, duration_days, complexity, team_df, module_df)
    task_df = merge_task_defaults(regenerated_task_df, st.session_state.get("roadmap_task_df"))

    st.markdown("### 6. Detailed Task Breakdown")
    st.markdown(
        "<div class='roadmap-section-copy'>Tasks are pre-built by phase and tailored to the project profile. Edit effort, team ownership, execution mode, or dependency chains and the roadmap will reflow instantly.</div>",
        unsafe_allow_html=True,
    )
    task_editor = st.data_editor(
        task_df,
        key="roadmap_task_editor",
        use_container_width=True,
        hide_index=True,
        num_rows="dynamic",
        column_config={
            "Task Key": st.column_config.TextColumn("Task Key", width="small", required=True),
            "Phase": st.column_config.SelectboxColumn("Phase", options=ROADMAP_PHASES, required=True),
            "Task Name": st.column_config.TextColumn("Task Name", width="large", required=True),
            "Team Responsible": st.column_config.SelectboxColumn("Team Responsible", options=sorted(team_df["Team"].tolist()), required=True),
            "Effort Days": st.column_config.NumberColumn("Effort Days", min_value=1, max_value=180, step=1),
            "Execution": st.column_config.SelectboxColumn("Execution", options=EXECUTION_OPTIONS, required=True),
            "Build Strategy": st.column_config.SelectboxColumn("Build Strategy", options=BUILD_OPTIONS, required=True),
            "Reuse Reduction %": st.column_config.NumberColumn("Reuse Reduction %", min_value=0, max_value=80, step=5),
            "Dependency": st.column_config.TextColumn("Dependency", width="medium"),
            "Reuse Dependency": st.column_config.TextColumn("Dependency Notes", width="large"),
        },
    )
    task_df = clean_task_df(task_editor)
    st.session_state["roadmap_task_df"] = task_df

    roadmap_df, holiday_dates, working_start = schedule_tasks(task_df, team_df, start_day, holiday_df)
    actual_end = roadmap_df["End Date"].max()
    actual_workdays = working_day_index(working_start, actual_end, holiday_dates) + 1
    variance_days = actual_workdays - duration_days
    critical_path = compute_critical_path(task_df)
    roadmap_df = attach_risk_levels(roadmap_df, task_df, team_df, critical_path)
    utilization_df = build_team_utilization(roadmap_df, team_df, working_start, actual_end, holiday_dates)
    bottlenecks = utilization_df[utilization_df["Utilization"] >= 0.75].copy()
    overload_df = clean_team_df(team_df)
    overload_df["Gap"] = overload_df["Resources"] - overload_df["Suggested Resources"]
    overloaded_teams = overload_df[overload_df["Gap"] < 0]
    overall_risk = "Low"
    if not roadmap_df[roadmap_df["Risk"] == "High"].empty or variance_days > 10 or not overloaded_teams.empty:
        overall_risk = "High"
    elif not roadmap_df[roadmap_df["Risk"] == "Medium"].empty or variance_days > 0:
        overall_risk = "Medium"

    timeline_summary_df = pd.DataFrame(
        [
            {"Metric": "Selected Start Date", "Value": start_day.strftime("%d %b %Y")},
            {"Metric": "Working Start Date", "Value": working_start.strftime("%d %b %Y")},
            {"Metric": "Target End Date", "Value": target_end.strftime("%d %b %Y")},
            {"Metric": "Roadmap End Date", "Value": actual_end.strftime("%d %b %Y")},
            {"Metric": "Target Working Days", "Value": duration_days},
            {"Metric": "Current Roadmap Working Days", "Value": actual_workdays},
            {"Metric": "Schedule Variance", "Value": variance_days},
        ]
    )
    utilization_df["Capacity Status"] = utilization_df["Utilization"].apply(
        lambda value: "Over Allocated" if value >= 0.9 else "Idle Capacity" if value < 0.45 else "Balanced"
    )
    utilization_df["Utilization %"] = (utilization_df["Utilization"] * 100).round(1)

    gantt_figure = build_gantt_figure(roadmap_df)
    resource_load_figure = px.bar(
        utilization_df,
        x="Team",
        y="Utilization %",
        color="Capacity Status",
        text="Utilization %",
        color_discrete_map={
            "Over Allocated": "#d97706",
            "Balanced": "#2457d6",
            "Idle Capacity": "#10b981",
        },
        hover_data={
            "Resources": True,
            "Allocation %": True,
            "Effective Capacity": True,
            "Assigned Task Days": True,
            "Idle Capacity Days": True,
            "Utilization %": False,
        },
        title="Resource Load View",
    )
    resource_load_figure.update_layout(
        margin=dict(t=52, l=10, r=10, b=10),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Manrope, Segoe UI, sans-serif", color="#334155"),
        title=dict(font=dict(size=18, color="#0f172a"), x=0.02),
        legend=dict(orientation="h", y=1.02, x=0),
        yaxis_title="Utilization %",
        xaxis_title="Team",
    )
    resource_load_figure.update_traces(texttemplate="%{text:.0f}%", textposition="outside")

    st.markdown("### 7. Roadmap Table")
    roadmap_display_df = roadmap_df[
        [
            "Task Name",
            "Phase",
            "Team Responsible",
            "Start Date",
            "End Date",
            "Duration",
            "Execution",
            "Dependency",
            "Status",
            "Risk",
            "Critical Path",
        ]
    ].copy()
    st.dataframe(roadmap_display_df, use_container_width=True, hide_index=True, height=min(600, 80 + len(roadmap_display_df) * 35))

    gantt_text = build_gantt_text(roadmap_df, working_start, holiday_dates)

    bottom_cols = st.columns([1.35, 0.95], gap="large")
    with bottom_cols[0]:
        st.markdown("### 8. Gantt Timeline View")
        st.plotly_chart(gantt_figure, use_container_width=True)
        with st.expander("Open text-based Gantt view", expanded=False):
            st.markdown(f"<div class='gantt-shell'><pre>{gantt_text}</pre></div>", unsafe_allow_html=True)
        st.markdown("### Resource Load View")
        st.plotly_chart(resource_load_figure, use_container_width=True)
        st.dataframe(
            utilization_df[["Team", "Resources", "Allocation %", "Assigned Task Days", "Utilization %", "Capacity Status", "Idle Capacity Days"]],
            use_container_width=True,
            hide_index=True,
        )

    with bottom_cols[1]:
        st.markdown("### Risks & Recommendations")
        risk_class = "risk-high" if overall_risk == "High" else "risk-medium" if overall_risk == "Medium" else "risk-low"
        st.markdown(
            f"""
            <div class="workspace-detail-card" style="margin-bottom:16px;">
                <h4>Risk Outlook</h4>
                <div class="roadmap-risk-pill {risk_class}">{overall_risk} delivery risk</div>
                <p style="margin-top:12px;">Critical path: {' -> '.join(critical_path) if critical_path else 'Not available'}</p>
                <p style="margin-top:8px;">Schedule variance: {variance_days:+} working day(s)</p>
            </div>
            """,
            unsafe_allow_html=True,
        )

        if not bottlenecks.empty:
            bottleneck_lines = "".join(
                f"<span class='roadmap-pill'>{row['Team']}: {row['Utilization'] * 100:.0f}% utilization</span>"
                for row in bottlenecks.head(4).to_dict(orient="records")
            )
            st.markdown(
                f"""
                <div class="workspace-detail-card" style="margin-bottom:16px;">
                    <h4>Bottlenecks</h4>
                    <p>Teams with the highest planned demand in the current schedule.</p>
                    <div>{bottleneck_lines}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

        if not overloaded_teams.empty:
            overload_lines = "".join(
                f"<span class='roadmap-pill'>{row['Team']}: {abs(int(row['Gap']))} below suggested</span>"
                for row in overloaded_teams.head(4).to_dict(orient="records")
            )
            st.markdown(
                f"""
                <div class="workspace-detail-card" style="margin-bottom:16px;">
                    <h4>Resource Overload</h4>
                    <p>These teams are staffed below the recommended planning baseline for the current scope.</p>
                    <div>{overload_lines}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

        recommendations = build_recommendations(roadmap_df, utilization_df, critical_path, complexity, target_end, actual_end, team_df)
        recommendation_html = "".join(f"<li>{item}</li>" for item in recommendations)
        st.markdown(
            f"""
            <div class="workspace-detail-card">
                <h4>Recommendations</h4>
                <ul>{recommendation_html}</ul>
            </div>
            """,
            unsafe_allow_html=True,
        )

    workbook_bytes = build_export_workbook(
        project_summary_df,
        market_df,
        timeline_summary_df,
        team_df,
        module_df,
        task_df,
        roadmap_df,
        roadmap_df[["Task Name", "Phase", "Team Responsible", "Start Date", "End Date", "Risk", "Dependency"]].copy(),
        holiday_df,
        gantt_text,
    )
    pdf_bytes = build_roadmap_pdf(
        project_name or "Enterprise Project Roadmap",
        project_description,
        project_summary_df,
        market_df,
        timeline_summary_df,
        roadmap_df,
        recommendations,
    )

    export_cols = st.columns([1, 1, 4], gap="small")
    export_cols[0].download_button(
        "Download Excel",
        data=workbook_bytes,
        file_name=f"{slugify(project_name or 'project_roadmap')}_roadmap.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        type="primary",
        use_container_width=True,
    )
    export_cols[1].download_button(
        "Download PDF",
        data=pdf_bytes,
        file_name=f"{slugify(project_name or 'project_roadmap')}_summary.pdf",
        mime="application/pdf",
        type="secondary",
        use_container_width=True,
    )
