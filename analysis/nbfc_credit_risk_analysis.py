"""
NBFC Loan Portfolio & Credit Risk Analytics
--------------------------------------------
Purpose:
    Perform customer, portfolio, credit-risk, delinquency, collection,
    recovery, and management-priority analysis using pandas and NumPy.

Input:
    NBFC_Loan_Portfolio_Credit_Risk_Analytics.xlsx

Output:
    NBFC_Python_Analytics_Output.xlsx

The analytical logic follows the original project. The main improvement is
code organization, naming, spacing, reusable functions, and readable output.
"""

import numpy as np
import pandas as pd


# ============================================================================
# CONFIGURATION
# ============================================================================

file_path = (
    "/storage/emulated/0/Project 2.0/"
    "NBFC_Loan_Portfolio_Credit_Risk_Analytics.xlsx"
)

OUTPUT_FILE = (
    "/storage/emulated/0/Project 2.0/"
    "NBFC_Python_Analytics_Output.xlsx"
)


# ============================================================================
# DATA LOADING
# ============================================================================

def load_data(file_path):
    """Load all source tables from the analytical workbook."""

    customers = pd.read_excel(file_path, sheet_name="Customers")
    loan_applications = pd.read_excel(
        file_path, sheet_name="Loan_Applications"
    )
    loans = pd.read_excel(file_path, sheet_name="Loans")
    repayments = pd.read_excel(file_path, sheet_name="Repayments")
    collections = pd.read_excel(file_path, sheet_name="Collections")
    loan_products = pd.read_excel(file_path, sheet_name="Loan_Products")
    branches = pd.read_excel(file_path, sheet_name="Branches")

    return (
        customers,
        loan_applications,
        loans,
        repayments,
        collections,
        loan_products,
        branches,
    )


# ============================================================================
# TASK 1 — CUSTOMER ANALYTICS
# ============================================================================

def create_customer_analysis(customers, loans, repayments):
    """Create the customer-level analytical dataset."""

    # Customer loan metrics
    customer_loans = (
        loans.groupby("Customer_ID")
        .agg(
            Total_Loans=("Loan_ID", "count"),
            Total_Loan_Amount=("Loan_Amount", "sum"),
            Avg_Loan_Amount=("Loan_Amount", "mean"),
        )
        .reset_index()
    )

    # Customer repayment metrics
    customer_repayments = (
        repayments.groupby("Customer_ID")
        .agg(
            Total_Repayments=("Payment_ID", "count"),
            Fully_Paid=(
                "Payment_Performance",
                lambda x: (x == "Fully Paid").sum(),
            ),
            Partially_Paid=(
                "Payment_Performance",
                lambda x: (x == "Partially Paid").sum(),
            ),
            Missed_Payments=(
                "Payment_Performance",
                lambda x: (x == "Missed").sum(),
            ),
            Avg_DPD=("DPD", "mean"),
            Max_DPD=("DPD", "max"),
        )
        .reset_index()
    )

    # Payment success rate
    customer_repayments["Payment_Success_Rate"] = (
        customer_repayments["Fully_Paid"]
        / customer_repayments["Total_Repayments"]
    )

    # Combine customer, loan, and repayment information
    customer_analysis = (
        customers
        .merge(customer_loans, on="Customer_ID", how="left")
        .merge(customer_repayments, on="Customer_ID", how="left")
    )

    # Risk segmentation
    customer_analysis["Risk_Segment"] = np.select(
        [
            (
                (customer_analysis["Credit_Score"] < 650)
                | (customer_analysis["Avg_DPD"] > 30)
                | (customer_analysis["Payment_Success_Rate"] < 0.50)
            ),
            (
                customer_analysis["Credit_Score"].between(650, 699)
                | customer_analysis["Avg_DPD"].between(15, 30)
                | customer_analysis["Payment_Success_Rate"].between(
                    0.50, 0.75
                )
            ),
        ],
        [
            "High Risk",
            "Medium Risk",
        ],
        default="Low Risk",
    )

    return customer_analysis


def create_customer_summaries(customer_analysis):
    """Create customer-level risk, income, employment, and exposure summaries."""

    # Risk summary
    risk_summary = (
        customer_analysis.groupby("Risk_Segment")
        .agg(
            Customers=("Customer_ID", "count"),
            Avg_Credit_Score=("Credit_Score", "mean"),
            Avg_DPD=("Avg_DPD", "mean"),
            Avg_Payment_Success=("Payment_Success_Rate", "mean"),
            Total_Loan_Exposure=("Total_Loan_Amount", "sum"),
        )
        .reset_index()
    )

    # Income segmentation
    customer_analysis["Income_Segment"] = np.select(
        [
            customer_analysis["Annual_Income"] < 300000,
            customer_analysis["Annual_Income"].between(300000, 600000),
            customer_analysis["Annual_Income"].between(600000, 1000000),
        ],
        [
            "Low Income",
            "Middle Income",
            "High Income",
        ],
        default="Very High Income",
    )

    # Income analysis
    income_analysis = (
        customer_analysis.groupby("Income_Segment")
        .agg(
            Customers=("Customer_ID", "count"),
            Avg_Income=("Annual_Income", "mean"),
            Avg_Credit_Score=("Credit_Score", "mean"),
            Total_Loan_Exposure=("Total_Loan_Amount", "sum"),
            Avg_Loan_Amount=("Avg_Loan_Amount", "mean"),
        )
        .reset_index()
    )

    # Employment analysis
    employment_analysis = (
        customer_analysis.groupby("Employment_Type")
        .agg(
            Customers=("Customer_ID", "count"),
            Avg_Income=("Annual_Income", "mean"),
            Avg_Credit_Score=("Credit_Score", "mean"),
            Total_Loan_Exposure=("Total_Loan_Amount", "sum"),
            Avg_Loan_Amount=("Avg_Loan_Amount", "mean"),
        )
        .reset_index()
    )

    # Customer loan concentration
    customer_analysis["Exposure_Rank"] = (
        customer_analysis["Total_Loan_Amount"]
        .rank(method="dense", ascending=False)
    )

    # High exposure + high risk customers
    exposure_threshold = customer_analysis["Total_Loan_Amount"].quantile(0.75)

    high_exposure_risk = customer_analysis[
        (customer_analysis["Risk_Segment"] == "High Risk")
        & (customer_analysis["Total_Loan_Amount"] >= exposure_threshold)
    ]

    return (
        risk_summary,
        income_analysis,
        employment_analysis,
        high_exposure_risk,
    )


# ============================================================================
# TASK 2 — LOAN-LEVEL CREDIT RISK ANALYTICS
# ============================================================================

def create_loan_risk_analysis(loans, customer_analysis):
    """Create loan-level risk data and portfolio risk summaries."""

    loan_risk = loans.merge(
        customer_analysis[
            [
                "Customer_ID",
                "Credit_Score",
                "Annual_Income",
                "Employment_Type",
                "Risk_Segment",
            ]
        ],
        on="Customer_ID",
        how="left",
    )

    # Risk by loan product
    product_risk = (
        loan_risk.groupby("Product_ID")
        .agg(
            Loans=("Loan_ID", "count"),
            Total_Exposure=("Loan_Amount", "sum"),
            Avg_Loan_Amount=("Loan_Amount", "mean"),
            Avg_Credit_Score=("Credit_Score", "mean"),
        )
        .reset_index()
    )

    # Risk segment vs portfolio exposure
    risk_exposure = (
        loan_risk.groupby("Risk_Segment")
        .agg(
            Loans=("Loan_ID", "count"),
            Total_Exposure=("Loan_Amount", "sum"),
            Avg_Loan_Amount=("Loan_Amount", "mean"),
            Avg_Credit_Score=("Credit_Score", "mean"),
        )
        .reset_index()
    )

    # Credit score band
    loan_risk["Credit_Band"] = np.select(
        [
            loan_risk["Credit_Score"] < 600,
            loan_risk["Credit_Score"].between(600, 649),
            loan_risk["Credit_Score"].between(650, 699),
            loan_risk["Credit_Score"].between(700, 749),
            loan_risk["Credit_Score"] >= 750,
        ],
        [
            "Very Poor",
            "Poor",
            "Fair",
            "Good",
            "Excellent",
        ],
        default="Unknown",
    )

    # Credit score vs exposure
    credit_exposure = (
        loan_risk.groupby("Credit_Band")
        .agg(
            Loans=("Loan_ID", "count"),
            Total_Exposure=("Loan_Amount", "sum"),
            Avg_Loan_Amount=("Loan_Amount", "mean"),
            Avg_Credit_Score=("Credit_Score", "mean"),
        )
        .reset_index()
    )

    # High-risk, high-value loans
    loan_threshold = loan_risk["Loan_Amount"].quantile(0.75)

    high_risk_high_value = loan_risk[
        (loan_risk["Risk_Segment"] == "High Risk")
        & (loan_risk["Loan_Amount"] >= loan_threshold)
    ]

    return (
        loan_risk,
        product_risk,
        risk_exposure,
        credit_exposure,
        high_risk_high_value,
    )


# ============================================================================
# TASK 3 — DELINQUENCY & PAYMENT BEHAVIOR ANALYTICS
# ============================================================================

def create_payment_behavior_analysis(repayments, customer_analysis):
    """Analyze customer payment behavior and delinquency."""

    payment_behavior = (
        repayments.groupby("Customer_ID")
        .agg(
            Total_Payments=("Payment_ID", "count"),
            Fully_Paid=(
                "Payment_Performance",
                lambda x: (x == "Fully Paid").sum(),
            ),
            Partially_Paid=(
                "Payment_Performance",
                lambda x: (x == "Partially Paid").sum(),
            ),
            Missed_Payments=(
                "Payment_Performance",
                lambda x: (x == "Missed").sum(),
            ),
            Avg_DPD=("DPD", "mean"),
            Max_DPD=("DPD", "max"),
        )
        .reset_index()
    )

    # Payment success rate
    payment_behavior["Payment_Success_Rate"] = (
        payment_behavior["Fully_Paid"]
        / payment_behavior["Total_Payments"]
    )

    # Delinquency level
    payment_behavior["Delinquency_Level"] = np.select(
        [
            payment_behavior["Max_DPD"] == 0,
            payment_behavior["Max_DPD"].between(1, 30),
            payment_behavior["Max_DPD"].between(31, 60),
            payment_behavior["Max_DPD"].between(61, 90),
            payment_behavior["Max_DPD"] > 90,
        ],
        [
            "Current",
            "1-30 DPD",
            "31-60 DPD",
            "61-90 DPD",
            "90+ DPD",
        ],
        default="Unknown",
    )

    # Delinquency summary
    delinquency_summary = (
        payment_behavior.groupby("Delinquency_Level")
        .agg(
            Customers=("Customer_ID", "count"),
            Avg_DPD=("Avg_DPD", "mean"),
            Avg_Payment_Success=("Payment_Success_Rate", "mean"),
            Total_Missed=("Missed_Payments", "sum"),
        )
        .reset_index()
    )

    # Risk segment vs payment behavior
    payment_risk = payment_behavior.merge(
        customer_analysis[
            [
                "Customer_ID",
                "Credit_Score",
                "Risk_Segment",
                "Total_Loan_Amount",
            ]
        ],
        on="Customer_ID",
        how="left",
    )

    risk_payment_summary = (
        payment_risk.groupby("Risk_Segment")
        .agg(
            Customers=("Customer_ID", "count"),
            Avg_Credit_Score=("Credit_Score", "mean"),
            Avg_DPD=("Avg_DPD", "mean"),
            Avg_Payment_Success=("Payment_Success_Rate", "mean"),
            Total_Missed_Payments=("Missed_Payments", "sum"),
            Total_Exposure=("Total_Loan_Amount", "sum"),
        )
        .reset_index()
    )

    # Repeat payment issues
    payment_behavior["Payment_Risk"] = np.select(
        [
            payment_behavior["Missed_Payments"] >= 3,
            payment_behavior["Missed_Payments"].between(1, 2),
            payment_behavior["Missed_Payments"] == 0,
        ],
        [
            "Repeat Missed",
            "Occasional Missed",
            "No Missed Payment",
        ],
        default="Unknown",
    )

    payment_risk_summary = (
        payment_behavior.groupby("Payment_Risk")
        .agg(
            Customers=("Customer_ID", "count"),
            Avg_DPD=("Avg_DPD", "mean"),
            Avg_Payment_Success=("Payment_Success_Rate", "mean"),
            Total_Missed=("Missed_Payments", "sum"),
        )
        .reset_index()
    )

    # High exposure + delinquent customers
    exposure_threshold = payment_risk["Total_Loan_Amount"].quantile(0.75)

    high_exposure_delinquent = payment_risk[
        (payment_risk["Max_DPD"] >= 61)
        & (payment_risk["Total_Loan_Amount"] >= exposure_threshold)
    ]

    return (
        payment_behavior,
        delinquency_summary,
        payment_risk,
        risk_payment_summary,
        payment_risk_summary,
        high_exposure_delinquent,
    )


# ============================================================================
# TASK 4 — COLLECTION & RECOVERY ANALYTICS
# ============================================================================

def create_collection_analysis(collections, customer_analysis):
    """Analyze collection performance and recovery effectiveness."""

    total_due = collections["Amount_Due"].sum()
    total_recovered = collections["Amount_Recovered"].sum()
    total_outstanding = total_due - total_recovered
    overall_recovery_rate = total_recovered / total_due

    # Recovery by contact channel
    channel_recovery = (
        collections.groupby("Contact_Channel")
        .agg(
            Collection_Records=("Collection_ID", "count"),
            Amount_Due=("Amount_Due", "sum"),
            Amount_Recovered=("Amount_Recovered", "sum"),
        )
        .reset_index()
    )

    channel_recovery["Recovery_Rate"] = (
        channel_recovery["Amount_Recovered"]
        / channel_recovery["Amount_Due"]
    )

    channel_recovery["Outstanding"] = (
        channel_recovery["Amount_Due"]
        - channel_recovery["Amount_Recovered"]
    )

    channel_recovery = channel_recovery.sort_values(
        "Recovery_Rate",
        ascending=False,
    )

    # Recovery by collection action
    action_recovery = (
        collections.groupby("Collection_Action")
        .agg(
            Collection_Records=("Collection_ID", "count"),
            Amount_Due=("Amount_Due", "sum"),
            Amount_Recovered=("Amount_Recovered", "sum"),
        )
        .reset_index()
    )

    action_recovery["Recovery_Rate"] = (
        action_recovery["Amount_Recovered"]
        / action_recovery["Amount_Due"]
    )

    action_recovery["Outstanding"] = (
        action_recovery["Amount_Due"]
        - action_recovery["Amount_Recovered"]
    )

    action_recovery = action_recovery.sort_values(
        "Recovery_Rate",
        ascending=False,
    )

    # Recovery by DPD stage
    dpd_recovery = (
        collections.groupby("DPD_At_Contact")
        .agg(
            Collection_Records=("Collection_ID", "count"),
            Amount_Due=("Amount_Due", "sum"),
            Amount_Recovered=("Amount_Recovered", "sum"),
        )
        .reset_index()
    )

    dpd_recovery["Recovery_Rate"] = (
        dpd_recovery["Amount_Recovered"]
        / dpd_recovery["Amount_Due"]
    )

    dpd_recovery["Outstanding"] = (
        dpd_recovery["Amount_Due"]
        - dpd_recovery["Amount_Recovered"]
    )

    # Collection status analysis
    status_analysis = (
        collections.groupby("Collection_Status")
        .agg(
            Records=("Collection_ID", "count"),
            Amount_Due=("Amount_Due", "sum"),
            Amount_Recovered=("Amount_Recovered", "sum"),
        )
        .reset_index()
    )

    status_analysis["Recovery_Rate"] = (
        status_analysis["Amount_Recovered"]
        / status_analysis["Amount_Due"]
    )

    # Collection priority cases
    collection_analysis = collections.merge(
        customer_analysis[
            [
                "Customer_ID",
                "Credit_Score",
                "Risk_Segment",
                "Total_Loan_Amount",
            ]
        ],
        on="Customer_ID",
        how="left",
    )

    collection_analysis["Outstanding"] = (
        collection_analysis["Amount_Due"]
        - collection_analysis["Amount_Recovered"]
    )

    priority_cases = collection_analysis[
        (collection_analysis["Risk_Segment"] == "High Risk")
        & (collection_analysis["DPD_At_Contact"] >= 61)
        & (collection_analysis["Outstanding"] > 0)
    ]

    return (
        total_due,
        total_recovered,
        total_outstanding,
        overall_recovery_rate,
        channel_recovery,
        action_recovery,
        dpd_recovery,
        status_analysis,
        collection_analysis,
        priority_cases,
    )


# ============================================================================
# TASK 5 — CROSS-DATASET BUSINESS ANALYSIS
# ============================================================================

def create_business_analysis(
    loans,
    repayments,
    collections,
    collection_analysis,
):
    """Combine portfolio, payment, and collection data for business analysis."""

    # Loan + repayment data
    loan_product = loans.merge(
        repayments[
            [
                "Loan_ID",
                "DPD",
                "Payment_Performance",
            ]
        ],
        on="Loan_ID",
        how="left",
    )

    # Product business performance
    product_business = (
        loan_product.groupby("Product_ID")
        .agg(
            Loans=("Loan_ID", "nunique"),
            Total_Exposure=("Loan_Amount", "sum"),
            Avg_Loan_Amount=("Loan_Amount", "mean"),
            Avg_DPD=("DPD", "mean"),
            Missed_Payments=(
                "Payment_Performance",
                lambda x: (x == "Missed").sum(),
            ),
            Partial_Payments=(
                "Payment_Performance",
                lambda x: (x == "Partially Paid").sum(),
            ),
        )
        .reset_index()
    )

    # Collection performance by loan
    product_collection = (
        collections.groupby("Loan_ID")
        .agg(
            Amount_Due=("Amount_Due", "sum"),
            Amount_Recovered=("Amount_Recovered", "sum"),
        )
        .reset_index()
    )

    product_collection["Outstanding"] = (
        product_collection["Amount_Due"]
        - product_collection["Amount_Recovered"]
    )

    # Combine product, payment, and collection data
    product_full = loan_product.merge(
        product_collection,
        on="Loan_ID",
        how="left",
    )

    product_summary = (
        product_full.groupby("Product_ID")
        .agg(
            Loans=("Loan_ID", "nunique"),
            Total_Exposure=("Loan_Amount", "sum"),
            Avg_DPD=("DPD", "mean"),
            Amount_Due=("Amount_Due", "sum"),
            Amount_Recovered=("Amount_Recovered", "sum"),
            Outstanding=("Outstanding", "sum"),
        )
        .reset_index()
    )

    product_summary["Recovery_Rate"] = (
        product_summary["Amount_Recovered"]
        / product_summary["Amount_Due"]
    )

    # Product risk priority score
    product_summary["Exposure_Score"] = (
        product_summary["Total_Exposure"]
        / product_summary["Total_Exposure"].max()
    )

    product_summary["DPD_Score"] = (
        product_summary["Avg_DPD"]
        / product_summary["Avg_DPD"].max()
    )

    product_summary["Outstanding_Score"] = (
        product_summary["Outstanding"]
        / product_summary["Outstanding"].max()
    )

    product_summary["Risk_Priority_Score"] = (
        product_summary["Exposure_Score"] * 0.40
        + product_summary["DPD_Score"] * 0.30
        + product_summary["Outstanding_Score"] * 0.30
    )

    product_priority = product_summary.sort_values(
        "Risk_Priority_Score",
        ascending=False,
    )

    # Risk segment vs collection performance
    risk_collection = (
        collection_analysis.groupby("Risk_Segment")
        .agg(
            Customers=("Customer_ID", "nunique"),
            Collection_Records=("Collection_ID", "count"),
            Amount_Due=("Amount_Due", "sum"),
            Amount_Recovered=("Amount_Recovered", "sum"),
            Outstanding=("Outstanding", "sum"),
        )
        .reset_index()
    )

    risk_collection["Recovery_Rate"] = (
        risk_collection["Amount_Recovered"]
        / risk_collection["Amount_Due"]
    )

    return (
        loan_product,
        product_business,
        product_collection,
        product_summary,
        product_priority,
        risk_collection,
    )


# ============================================================================
# TASK 6 — CUSTOMER MANAGEMENT ANALYSIS
# ============================================================================

def create_customer_management_analysis(
    customer_analysis,
    collection_analysis,
):
    """Identify high-risk customers requiring management attention."""

    customer_management = customer_analysis.merge(
        collection_analysis.groupby("Customer_ID")
        .agg(
            Collection_Due=("Amount_Due", "sum"),
            Recovered=("Amount_Recovered", "sum"),
            Outstanding=("Outstanding", "sum"),
        )
        .reset_index(),
        on="Customer_ID",
        how="left",
    )

    collection_columns = [
        "Collection_Due",
        "Recovered",
        "Outstanding",
    ]

    customer_management[collection_columns] = (
        customer_management[collection_columns].fillna(0)
    )

    customer_management["Recovery_Rate"] = np.where(
        customer_management["Collection_Due"] > 0,
        customer_management["Recovered"]
        / customer_management["Collection_Due"],
        0,
    )

    # Critical customers:
    # High Risk + top 25% exposure + outstanding amount
    critical_customers = customer_management[
        (customer_management["Risk_Segment"] == "High Risk")
        & (
            customer_management["Total_Loan_Amount"]
            >= customer_management["Total_Loan_Amount"].quantile(0.75)
        )
        & (customer_management["Outstanding"] > 0)
    ]

    return customer_management, critical_customers


# ============================================================================
# TASK 7 — MANAGEMENT INSIGHTS DATASETS
# ============================================================================

def create_management_datasets(
    product_summary,
    customer_management,
):
    """Create product, risk, and collection management datasets."""

    # Product management dataset
    product_management = product_summary.copy()

    product_management["Exposure_Share"] = (
        product_management["Total_Exposure"]
        / product_management["Total_Exposure"].sum()
    )

    product_management["Outstanding_Share"] = (
        product_management["Outstanding"]
        / product_management["Outstanding"].sum()
    )

    product_management["Risk_Level"] = np.select(
        [
            product_management["Risk_Priority_Score"] >= 0.75,
            product_management["Risk_Priority_Score"] >= 0.50,
        ],
        [
            "High Priority",
            "Medium Priority",
        ],
        default="Low Priority",
    )

    # Risk management dataset
    risk_management = (
        customer_management.groupby("Risk_Segment")
        .agg(
            Customers=("Customer_ID", "count"),
            Total_Exposure=("Total_Loan_Amount", "sum"),
            Avg_Credit_Score=("Credit_Score", "mean"),
            Avg_DPD=("Avg_DPD", "mean"),
            Avg_Payment_Success=("Payment_Success_Rate", "mean"),
            Collection_Due=("Collection_Due", "sum"),
            Recovered=("Recovered", "sum"),
            Outstanding=("Outstanding", "sum"),
        )
        .reset_index()
    )

    risk_management["Exposure_Share"] = (
        risk_management["Total_Exposure"]
        / risk_management["Total_Exposure"].sum()
    )

    risk_management["Recovery_Rate"] = np.where(
        risk_management["Collection_Due"] > 0,
        risk_management["Recovered"]
        / risk_management["Collection_Due"],
        0,
    )

    return product_management, risk_management


def create_collection_management_dataset(collections):
    """Create collection-channel management metrics."""

    collection_management = (
        collections.groupby("Contact_Channel")
        .agg(
            Collection_Records=("Collection_ID", "count"),
            Amount_Due=("Amount_Due", "sum"),
            Amount_Recovered=("Amount_Recovered", "sum"),
        )
        .reset_index()
    )

    collection_management["Outstanding"] = (
        collection_management["Amount_Due"]
        - collection_management["Amount_Recovered"]
    )

    collection_management["Recovery_Rate"] = (
        collection_management["Amount_Recovered"]
        / collection_management["Amount_Due"]
    )

    collection_management["Recovery_Rank"] = (
        collection_management["Recovery_Rate"]
        .rank(method="dense", ascending=False)
    )

    return collection_management


# ============================================================================
# TASK 8 — EXECUTIVE KPI DATASET
# ============================================================================

def create_executive_kpis(
    loan_applications,
    loans,
    repayments,
    collections,
):
    """Create the executive-level portfolio KPI dataset."""

    total_applications = len(loan_applications)
    approved_applications = (
        loan_applications["Application_Status"] == "Approved"
    ).sum()

    total_due = collections["Amount_Due"].sum()
    total_recovered = collections["Amount_Recovered"].sum()

    executive_kpis = {
        "Total_Applications": total_applications,
        "Approved_Applications": approved_applications,
        "Approval_Rate": approved_applications / total_applications,
        "Total_Loans": loans["Loan_ID"].nunique(),
        "Total_Exposure": loans["Loan_Amount"].sum(),
        "Average_Loan_Amount": loans["Loan_Amount"].mean(),
        "Active_Loans": (
            loans["Loan_Status"] == "Active"
        ).sum(),
        "Closed_Loans": (
            loans["Loan_Status"] == "Closed"
        ).sum(),
        "Total_Repayments": len(repayments),
        "Fully_Paid_Rate": (
            repayments["Payment_Performance"] == "Fully Paid"
        ).sum() / len(repayments),
        "Missed_Payment_Rate": (
            repayments["Payment_Performance"] == "Missed"
        ).sum() / len(repayments),
        "Overall_DPD_Rate": (
            repayments["DPD"] > 0
        ).sum() / len(repayments),
        "Severe_DPD_Rate": (
            repayments["DPD"] >= 61
        ).sum() / len(repayments),
        "Total_Amount_Due": total_due,
        "Total_Recovered": total_recovered,
        "Total_Outstanding": total_due - total_recovered,
        "Overall_Recovery_Rate": total_recovered / total_due,
    }

    return pd.DataFrame([executive_kpis])


# ============================================================================
# PHASE 5 — FINAL ANALYTICAL DATASETS
# ============================================================================

def create_portfolio_dataset(loan_risk, branches, repayments, loans):
    """Create product-region portfolio analysis with DPD metrics."""

    portfolio_dataset = loan_risk.merge(
        branches[["Branch_ID", "Region"]],
        on="Branch_ID",
        how="left",
    )

    portfolio_dataset = (
        portfolio_dataset.groupby(["Product_ID", "Region"])
        .agg(
            Total_Loans=("Loan_ID", "count"),
            Total_Exposure=("Loan_Amount", "sum"),
            Average_Loan_Amount=("Loan_Amount", "mean"),
            High_Risk_Loans=(
                "Risk_Segment",
                lambda x: (x == "High Risk").sum(),
            ),
        )
        .reset_index()
    )

    portfolio_dataset["High_Risk_Rate"] = (
        portfolio_dataset["High_Risk_Loans"]
        / portfolio_dataset["Total_Loans"]
    )

    # DPD metrics by loan
    loan_dpd = (
        repayments.groupby("Loan_ID")
        .agg(
            Average_DPD=("DPD", "mean"),
            Max_DPD=("DPD", "max"),
        )
        .reset_index()
    )

    loan_info = loans[
        ["Loan_ID", "Product_ID", "Branch_ID"]
    ].merge(
        branches[["Branch_ID", "Region"]],
        on="Branch_ID",
        how="left",
    )

    loan_dpd = loan_info.merge(
        loan_dpd,
        on="Loan_ID",
        how="left",
    )

    loan_dpd["DPD_Flag"] = loan_dpd["Average_DPD"] > 0

    dpd_summary = (
        loan_dpd.groupby(["Product_ID", "Region"])
        .agg(
            DPD_Loans=("DPD_Flag", "sum"),
            Avg_DPD=("Average_DPD", "mean"),
            Total_Loans_DPD=("Loan_ID", "count"),
        )
        .reset_index()
    )

    dpd_summary["DPD_Rate"] = (
        dpd_summary["DPD_Loans"]
        / dpd_summary["Total_Loans_DPD"]
    )

    # Merge portfolio and DPD data
    portfolio_dataset = portfolio_dataset.merge(
        dpd_summary[
            [
                "Product_ID",
                "Region",
                "DPD_Loans",
                "Avg_DPD",
                "DPD_Rate",
            ]
        ],
        on=["Product_ID", "Region"],
        how="left",
    )

    return portfolio_dataset


def create_credit_risk_dataset(customer_analysis):
    """Create the final customer-level credit risk dataset."""

    credit_risk_dataset = customer_analysis[
        [
            "Customer_ID",
            "Credit_Score",
            "Credit_Score_Band",
            "Annual_Income",
            "Income_Segment",
            "Employment_Type",
            "Risk_Segment",
            "Total_Loans",
            "Total_Loan_Amount",
            "Total_Repayments",
            "Avg_DPD",
            "Max_DPD",
            "Payment_Success_Rate",
        ]
    ].copy()

    credit_risk_dataset["High_Risk_Flag"] = (
        credit_risk_dataset["Risk_Segment"] == "High Risk"
    )

    credit_risk_dataset["Severe_DPD_Flag"] = (
        credit_risk_dataset["Max_DPD"] >= 61
    )

    credit_risk_summary = (
        credit_risk_dataset.groupby("Credit_Score_Band")
        .agg(
            Customers=("Customer_ID", "count"),
            Avg_Credit_Score=("Credit_Score", "mean"),
            Avg_DPD=("Avg_DPD", "mean"),
            Max_DPD=("Max_DPD", "max"),
            Total_Loan_Exposure=("Total_Loan_Amount", "sum"),
            High_Risk_Customers=("High_Risk_Flag", "sum"),
            Severe_DPD_Customers=("Severe_DPD_Flag", "sum"),
        )
        .reset_index()
    )

    return credit_risk_dataset, credit_risk_summary


def create_final_collection_dataset(collections):
    """Create the final collection performance dataset."""

    collection_dataset = collections.copy()

    collection_dataset["Outstanding_Amount"] = (
        collection_dataset["Amount_Due"]
        - collection_dataset["Amount_Recovered"]
    )

    collection_channel = (
        collection_dataset.groupby("Contact_Channel")
        .agg(
            Collection_Records=("Collection_ID", "count"),
            Total_Amount_Due=("Amount_Due", "sum"),
            Total_Recovered=("Amount_Recovered", "sum"),
            Total_Outstanding=("Outstanding_Amount", "sum"),
        )
        .reset_index()
    )

    collection_channel["Recovery_Rate"] = (
        collection_channel["Total_Recovered"]
        / collection_channel["Total_Amount_Due"]
    )

    collection_action = (
        collection_dataset.groupby("Collection_Action")
        .agg(
            Collection_Records=("Collection_ID", "count"),
            Total_Amount_Due=("Amount_Due", "sum"),
            Total_Recovered=("Amount_Recovered", "sum"),
            Total_Outstanding=("Outstanding_Amount", "sum"),
        )
        .reset_index()
    )

    collection_action["Recovery_Rate"] = (
        collection_action["Total_Recovered"]
        / collection_action["Total_Amount_Due"]
    )

    collection_dpd = (
        collection_dataset.groupby("DPD_At_Contact")
        .agg(
            Collection_Records=("Collection_ID", "count"),
            Total_Amount_Due=("Amount_Due", "sum"),
            Total_Recovered=("Amount_Recovered", "sum"),
            Total_Outstanding=("Outstanding_Amount", "sum"),
        )
        .reset_index()
    )

    collection_dpd["Recovery_Rate"] = (
        collection_dpd["Total_Recovered"]
        / collection_dpd["Total_Amount_Due"]
    )

    collection_summary = (
        collection_dataset.groupby("Collection_Status")
        .agg(
            Collection_Records=("Collection_ID", "count"),
            Total_Amount_Due=("Amount_Due", "sum"),
            Total_Recovered=("Amount_Recovered", "sum"),
            Total_Outstanding=("Outstanding_Amount", "sum"),
        )
        .reset_index()
    )

    collection_summary["Recovery_Rate"] = (
        collection_summary["Total_Recovered"]
        / collection_summary["Total_Amount_Due"]
    )

    return (
        collection_dataset,
        collection_channel,
        collection_action,
        collection_dpd,
        collection_summary,
    )


def create_customer_risk_dataset(
    customer_analysis,
    collections,
):
    """Create the final customer risk dataset with collection metrics."""

    customer_risk_dataset = customer_analysis.copy()

    customer_collection = (
        collections.groupby("Customer_ID")
        .agg(
            Collection_Records=("Collection_ID", "count"),
            Total_Amount_Due=("Amount_Due", "sum"),
            Total_Recovered=("Amount_Recovered", "sum"),
        )
        .reset_index()
    )

    customer_collection["Outstanding_Amount"] = (
        customer_collection["Total_Amount_Due"]
        - customer_collection["Total_Recovered"]
    )

    customer_collection["Recovery_Rate"] = (
        customer_collection["Total_Recovered"]
        / customer_collection["Total_Amount_Due"]
    )

    customer_risk_dataset = customer_risk_dataset.merge(
        customer_collection,
        on="Customer_ID",
        how="left",
    )

    collection_columns = [
        "Collection_Records",
        "Total_Amount_Due",
        "Total_Recovered",
        "Outstanding_Amount",
        "Recovery_Rate",
    ]

    customer_risk_dataset[collection_columns] = (
        customer_risk_dataset[collection_columns].fillna(0)
    )

    exposure_threshold = customer_risk_dataset[
        "Total_Loan_Amount"
    ].quantile(0.75)

    customer_risk_dataset["High_Exposure_Flag"] = (
        customer_risk_dataset["Total_Loan_Amount"]
        >= exposure_threshold
    )

    customer_risk_dataset["Critical_Customer_Flag"] = (
        (customer_risk_dataset["Risk_Segment"] == "High Risk")
        & (
            (customer_risk_dataset["Max_DPD"] >= 61)
            | customer_risk_dataset["High_Exposure_Flag"]
        )
    )

    final_columns = [
        "Customer_ID",
        "Age",
        "Gender",
        "City",
        "State",
        "Region",
        "Employment_Type",
        "Annual_Income",
        "Income_Segment",
        "Credit_Score",
        "Credit_Score_Band",
        "Risk_Segment",
        "Total_Loans",
        "Total_Loan_Amount",
        "Avg_Loan_Amount",
        "Total_Repayments",
        "Fully_Paid",
        "Partially_Paid",
        "Missed_Payments",
        "Payment_Success_Rate",
        "Avg_DPD",
        "Max_DPD",
        "Collection_Records",
        "Total_Amount_Due",
        "Total_Recovered",
        "Outstanding_Amount",
        "Recovery_Rate",
        "High_Exposure_Flag",
        "Critical_Customer_Flag",
    ]

    return customer_risk_dataset[final_columns].copy()


def create_management_priority_dataset(
    product_management,
    risk_management,
    collection_management,
):
    """Create the final management-priority table."""

    top_exposure_product = product_management.loc[
        product_management["Total_Exposure"].idxmax()
    ]

    top_risk_product = product_management.loc[
        product_management["Risk_Priority_Score"].idxmax()
    ]

    top_outstanding_risk = risk_management.loc[
        risk_management["Outstanding"].idxmax()
    ]

    best_collection_channel = collection_management.loc[
        collection_management["Recovery_Rate"].idxmax()
    ]

    management_priority = pd.DataFrame(
        {
            "Priority_Area": [
                "Portfolio Risk",
                "Delinquency",
                "Collection",
                "Product Monitoring",
                "Customer Monitoring",
            ],
            "Focus": [
                "High Risk Customers",
                "61+ DPD Customers",
                "High Outstanding Amount",
                "High Risk Priority Products",
                "High Risk + High Exposure Customers",
            ],
            "Recommended_Action": [
                "Enhanced credit monitoring",
                "Immediate collection intervention",
                "Prioritize recovery efforts",
                "Review product-level risk exposure",
                "Prioritize targeted collection",
            ],
        }
    )

    final_priorities = pd.DataFrame(
        {
            "Priority": [
                "Portfolio Exposure",
                "Credit Risk",
                "Delinquency",
                "Collections",
                "Customer Risk",
            ],
            "Focus_Area": [
                top_exposure_product["Product_ID"],
                top_risk_product["Product_ID"],
                "61+ DPD Customers",
                best_collection_channel["Contact_Channel"],
                "High Risk + High Exposure",
            ],
            "Management_Action": [
                "Monitor concentration and portfolio exposure",
                "Perform enhanced product-level risk monitoring",
                "Prioritize early collection intervention",
                "Increase usage of effective recovery channels",
                "Prioritize targeted monitoring and collection",
            ],
        }
    )

    return management_priority, final_priorities, top_outstanding_risk


# ============================================================================
# OUTPUT / DISPLAY FUNCTIONS
# ============================================================================

def print_dataset_check(name, dataframe):
    """Print a compact dataset validation summary."""

    print(f"\n===== {name} =====")
    print("Rows:", len(dataframe))
    print("Columns:", len(dataframe.columns))


def print_executive_summary(
    executive_kpis,
    critical_customers,
    high_risk_high_value,
    product_management,
    risk_management,
    collection_management,
):
    """Print a concise management-level summary."""

    kpi = executive_kpis.iloc[0]

    top_exposure_product = product_management.loc[
        product_management["Total_Exposure"].idxmax()
    ]

    top_risk_product = product_management.loc[
        product_management["Risk_Priority_Score"].idxmax()
    ]

    top_outstanding_risk = risk_management.loc[
        risk_management["Outstanding"].idxmax()
    ]

    best_collection_channel = collection_management.loc[
        collection_management["Recovery_Rate"].idxmax()
    ]

    print("\n" + "=" * 70)
    print("FINAL NBFC PORTFOLIO ANALYSIS")
    print("=" * 70)

    print("\n--- EXECUTIVE KPIs ---")
    print("Total Applications:", kpi["Total_Applications"])
    print("Approved Applications:", kpi["Approved_Applications"])
    print("Approval Rate:", round(kpi["Approval_Rate"] * 100, 2), "%")
    print("Total Loans:", kpi["Total_Loans"])
    print("Total Loan Exposure: ₹", round(kpi["Total_Exposure"], 2))
    print("Average Loan Amount: ₹", round(kpi["Average_Loan_Amount"], 2))
    print("Active Loans:", kpi["Active_Loans"])
    print("Closed Loans:", kpi["Closed_Loans"])
    print("Total Repayments:", kpi["Total_Repayments"])
    print("Fully Paid Rate:", round(kpi["Fully_Paid_Rate"] * 100, 2), "%")
    print(
        "Missed Payment Rate:",
        round(kpi["Missed_Payment_Rate"] * 100, 2),
        "%",
    )
    print("Overall DPD Rate:", round(kpi["Overall_DPD_Rate"] * 100, 2), "%")
    print(
        "Severe DPD Rate:",
        round(kpi["Severe_DPD_Rate"] * 100, 2),
        "%",
    )
    print(
        "Overall Recovery Rate:",
        round(kpi["Overall_Recovery_Rate"] * 100, 2),
        "%",
    )
    print("Total Outstanding: ₹", round(kpi["Total_Outstanding"], 2))

    print("\n--- TOP BUSINESS PRIORITIES ---")
    print(
        "Highest Exposure Product:",
        top_exposure_product["Product_ID"],
    )
    print(
        "Highest Risk Priority Product:",
        top_risk_product["Product_ID"],
    )
    print(
        "Highest Outstanding Risk Segment:",
        top_outstanding_risk["Risk_Segment"],
    )
    print(
        "Best Recovery Channel:",
        best_collection_channel["Contact_Channel"],
    )
    print("Critical Customers:", len(critical_customers))
    print("High Risk + High Value Loans:", len(high_risk_high_value))


# ============================================================================
# EXPORT
# ============================================================================

def export_analytical_workbook(
    output_file,
    executive_kpis,
    portfolio_dataset,
    credit_risk_dataset,
    collection_dataset,
    customer_risk_dataset,
    product_management,
):
    """Export all final analytical datasets to Excel."""

    with pd.ExcelWriter(
        output_file,
        engine="openpyxl",
    ) as writer:

        executive_kpis.to_excel(
            writer,
            sheet_name="Executive_KPIs",
            index=False,
        )

        portfolio_dataset.to_excel(
            writer,
            sheet_name="Portfolio_Analysis",
            index=False,
        )

        credit_risk_dataset.to_excel(
            writer,
            sheet_name="Credit_Risk",
            index=False,
        )

        collection_dataset.to_excel(
            writer,
            sheet_name="Collection_Performance",
            index=False,
        )

        customer_risk_dataset.to_excel(
            writer,
            sheet_name="Customer_Risk",
            index=False,
        )

        product_management.to_excel(
            writer,
            sheet_name="Management_Priorities",
            index=False,
        )


# ============================================================================
# MAIN WORKFLOW
# ============================================================================

def main():
    """Run selected NBFC analytics tasks from the configuration below."""

    # ========================================================================
    # CONFIGURATION
    # ========================================================================
    # Run one or more analyses by changing this list.
    #
    # Examples:
    #   ANALYSIS_TO_RUN = ["credit_risk"]
    #   ANALYSIS_TO_RUN = ["credit_risk", "collection"]
    #   ANALYSIS_TO_RUN = ["all"]
    #
    # Available options:
    #   customer            -> Customer Analytics
    #   credit_risk         -> Loan-Level Credit Risk Analytics
    #   payment_behavior    -> Delinquency & Payment Behavior Analytics
    #   collection          -> Collection & Recovery Analytics
    #   business            -> Cross-Dataset Business Analysis
    #   customer_management -> Customer Management Analysis
    #   management          -> Management Insights / Priorities
    #   executive_kpi       -> Executive KPI Analysis
    #   final_workbook      -> Complete Phase 5 workbook
    #   all                 -> Run the complete project
    # ========================================================================

    ANALYSIS_TO_RUN = ["credit_risk"]

    valid_analyses = {
        "customer",
        "credit_risk",
        "payment_behavior",
        "collection",
        "business",
        "customer_management",
        "management",
        "executive_kpi",
        "final_workbook",
        "all",
    }

    selected = set(ANALYSIS_TO_RUN)
    invalid = selected - valid_analyses

    if invalid:
        raise ValueError(
            f"Invalid analysis option(s): {sorted(invalid)}. "
            f"Valid options are: {sorted(valid_analyses)}"
        )

    if "all" in selected or "final_workbook" in selected:
        selected = valid_analyses - {"all"}

    print("=" * 70)
    print("NBFC LOAN PORTFOLIO & CREDIT RISK ANALYTICS")
    print("=" * 70)
    print("Analyses selected:", ", ".join(ANALYSIS_TO_RUN))

    # ========================================================================
    # LOAD SOURCE DATA
    # ========================================================================

    (
        customers,
        loan_applications,
        loans,
        repayments,
        collections,
        loan_products,
        branches,
    ) = load_data(file_path)

    print("\nSource data loaded successfully.")
    print("Customers:", len(customers))
    print("Loan Applications:", len(loan_applications))
    print("Loans:", len(loans))
    print("Repayments:", len(repayments))
    print("Collections:", len(collections))
    print("Loan Products:", len(loan_products))
    print("Branches:", len(branches))

    # ========================================================================
    # DATASET VARIABLES
    # ========================================================================
    # These are populated only when the selected analysis needs them.

    customer_analysis = None
    collection_analysis = None
    loan_risk = None
    payment_behavior = None
    product_summary = None
    customer_management = None
    product_management = None
    risk_management = None
    collection_management = None

    # ========================================================================
    # TASK 1 — CUSTOMER ANALYTICS
    # ========================================================================

    if "customer" in selected:
        customer_analysis = create_customer_analysis(
            customers,
            loans,
            repayments,
        )

        (
            risk_summary,
            income_analysis,
            employment_analysis,
            high_exposure_risk,
        ) = create_customer_summaries(customer_analysis)

        print_dataset_check("CUSTOMER ANALYSIS", customer_analysis)
        print("\nRisk Summary:")
        print(risk_summary)
        print("\nIncome Analysis:")
        print(income_analysis)
        print("\nEmployment Analysis:")
        print(employment_analysis)
        print("\nHigh Exposure + High Risk Customers:")
        print(high_exposure_risk.head(10))

    # ========================================================================
    # TASK 2 — LOAN-LEVEL CREDIT RISK ANALYTICS
    # ========================================================================

    if "credit_risk" in selected:
        if customer_analysis is None:
            customer_analysis = create_customer_analysis(
                customers,
                loans,
                repayments,
            )

        (
            loan_risk,
            product_risk,
            risk_exposure,
            credit_exposure,
            high_risk_high_value,
        ) = create_loan_risk_analysis(
            loans,
            customer_analysis,
        )

        print_dataset_check("LOAN RISK ANALYSIS", loan_risk)
        print("\nRisk by Loan Product:")
        print(product_risk)
        print("\nRisk Segment Exposure:")
        print(risk_exposure)
        print("\nCredit Score Exposure:")
        print(credit_exposure)
        print("\nHigh Risk + High Value Loans:")
        print(high_risk_high_value.head(10))

    # ========================================================================
    # TASK 3 — DELINQUENCY & PAYMENT BEHAVIOR ANALYTICS
    # ========================================================================

    if "payment_behavior" in selected:
        if customer_analysis is None:
            customer_analysis = create_customer_analysis(
                customers,
                loans,
                repayments,
            )

        (
            payment_behavior,
            delinquency_summary,
            payment_risk,
            risk_payment_summary,
            payment_risk_summary,
            high_exposure_delinquent,
        ) = create_payment_behavior_analysis(
            repayments,
            customer_analysis,
        )

        print_dataset_check("PAYMENT BEHAVIOR ANALYSIS", payment_behavior)
        print("\nDelinquency Summary:")
        print(delinquency_summary)
        print("\nRisk vs Payment Behavior:")
        print(payment_risk.head(10))
        print("\nHigh Exposure + Delinquent Customers:")
        print(high_exposure_delinquent.head(10))

    # ========================================================================
    # TASK 4 — COLLECTION & RECOVERY ANALYTICS
    # ========================================================================

    if "collection" in selected:
        if customer_analysis is None:
            customer_analysis = create_customer_analysis(
                customers,
                loans,
                repayments,
            )

        (
            total_due,
            total_recovered,
            total_outstanding,
            overall_recovery_rate,
            channel_recovery,
            action_recovery,
            dpd_recovery,
            status_analysis,
            collection_analysis,
            priority_cases,
        ) = create_collection_analysis(
            collections,
            customer_analysis,
        )

        print("\n===== COLLECTION & RECOVERY ANALYTICS =====")
        print("Total Due:", round(total_due, 2))
        print("Total Recovered:", round(total_recovered, 2))
        print("Total Outstanding:", round(total_outstanding, 2))
        print("Recovery Rate:", round(overall_recovery_rate * 100, 2), "%")
        print("\nRecovery by Contact Channel:")
        print(channel_recovery)
        print("\nRecovery by Collection Action:")
        print(action_recovery)
        print("\nRecovery by DPD Stage:")
        print(dpd_recovery)
        print("\nCollection Status:")
        print(status_analysis)
        print("\nPriority Collection Cases:")
        print(priority_cases.head(10))

    # ========================================================================
    # TASK 5 — CROSS-DATASET BUSINESS ANALYSIS
    # ========================================================================

    if "business" in selected:
        if customer_analysis is None:
            customer_analysis = create_customer_analysis(
                customers,
                loans,
                repayments,
            )

        if collection_analysis is None:
            (
                _total_due,
                _total_recovered,
                _total_outstanding,
                _overall_recovery_rate,
                _channel_recovery,
                _action_recovery,
                _dpd_recovery,
                _status_analysis,
                collection_analysis,
                _priority_cases,
            ) = create_collection_analysis(
                collections,
                customer_analysis,
            )

        (
            loan_product,
            product_business,
            product_collection,
            product_summary,
            product_priority,
            risk_collection,
        ) = create_business_analysis(
            loans,
            repayments,
            collections,
            collection_analysis,
        )

        print("\n===== CROSS-DATASET BUSINESS ANALYSIS =====")
        print("\nProduct Business Performance:")
        print(product_business)
        print("\nProduct Portfolio + Collection Performance:")
        print(product_summary)
        print("\nProduct Risk Priority:")
        print(product_priority)
        print("\nRisk vs Collection Performance:")
        print(risk_collection)

    # ========================================================================
    # TASK 6 — CUSTOMER MANAGEMENT ANALYSIS
    # ========================================================================

    if "customer_management" in selected:
        if customer_analysis is None:
            customer_analysis = create_customer_analysis(
                customers,
                loans,
                repayments,
            )

        if collection_analysis is None:
            (
                _total_due,
                _total_recovered,
                _total_outstanding,
                _overall_recovery_rate,
                _channel_recovery,
                _action_recovery,
                _dpd_recovery,
                _status_analysis,
                collection_analysis,
                _priority_cases,
            ) = create_collection_analysis(
                collections,
                customer_analysis,
            )

        customer_management, critical_customers = (
            create_customer_management_analysis(
                customer_analysis,
                collection_analysis,
            )
        )

        print("\n===== CUSTOMER MANAGEMENT ANALYSIS =====")
        print("\nCustomer Management Dataset:")
        print(customer_management.head(20))
        print("\nCritical Customers:")
        print(critical_customers.head(20))

    # ========================================================================
    # TASK 7 — MANAGEMENT INSIGHTS & PRIORITIES
    # ========================================================================

    if "management" in selected:
        if customer_analysis is None:
            customer_analysis = create_customer_analysis(
                customers,
                loans,
                repayments,
            )

        if collection_analysis is None:
            (
                _total_due,
                _total_recovered,
                _total_outstanding,
                _overall_recovery_rate,
                _channel_recovery,
                _action_recovery,
                _dpd_recovery,
                _status_analysis,
                collection_analysis,
                _priority_cases,
            ) = create_collection_analysis(
                collections,
                customer_analysis,
            )

        if product_summary is None:
            (
                _loan_product,
                _product_business,
                _product_collection,
                product_summary,
                _product_priority,
                _risk_collection,
            ) = create_business_analysis(
                loans,
                repayments,
                collections,
                collection_analysis,
            )

        if customer_management is None:
            customer_management, critical_customers = (
                create_customer_management_analysis(
                    customer_analysis,
                    collection_analysis,
                )
            )

        product_management, risk_management = create_management_datasets(
            product_summary,
            customer_management,
        )

        collection_management = create_collection_management_dataset(
            collections
        )

        (
            management_priority,
            final_priorities,
            top_outstanding_risk,
        ) = create_management_priority_dataset(
            product_management,
            risk_management,
            collection_management,
        )

        print("\n===== MANAGEMENT INSIGHTS & PRIORITIES =====")
        print("\nProduct Management:")
        print(product_management)
        print("\nRisk Management:")
        print(risk_management)
        print("\nCollection Management:")
        print(collection_management)
        print("\nManagement Priority:")
        print(management_priority)
        print("\nFinal Priorities:")
        print(final_priorities)
        print("\nHighest Outstanding Risk Segment:")
        print(top_outstanding_risk)

    # ========================================================================
    # TASK 8 — EXECUTIVE KPI ANALYSIS
    # ========================================================================

    executive_kpis = None

    if "executive_kpi" in selected:
        executive_kpis = create_executive_kpis(
            loan_applications,
            loans,
            repayments,
            collections,
        )

        print("\n===== EXECUTIVE KPI ANALYSIS =====")
        for column, value in executive_kpis.items():
            if isinstance(value, (float, np.floating)):
                if "Rate" in column:
                    print(column, ":", round(value * 100, 2), "%")
                else:
                    print(column, ":", round(value, 2))
            else:
                print(column, ":", value)

    # ========================================================================
    # FINAL WORKBOOK — COMPLETE PHASE 5 OUTPUT
    # ========================================================================

    if "final_workbook" in selected:
        # The final workbook requires the complete analytical pipeline.
        if customer_analysis is None:
            customer_analysis = create_customer_analysis(
                customers,
                loans,
                repayments,
            )

        if loan_risk is None:
            (
                loan_risk,
                _product_risk,
                _risk_exposure,
                _credit_exposure,
                _high_risk_high_value,
            ) = create_loan_risk_analysis(
                loans,
                customer_analysis,
            )

        if collection_analysis is None:
            (
                _total_due,
                _total_recovered,
                _total_outstanding,
                _overall_recovery_rate,
                _channel_recovery,
                _action_recovery,
                _dpd_recovery,
                _status_analysis,
                collection_analysis,
                _priority_cases,
            ) = create_collection_analysis(
                collections,
                customer_analysis,
            )

        if product_summary is None:
            (
                _loan_product,
                _product_business,
                _product_collection,
                product_summary,
                _product_priority,
                _risk_collection,
            ) = create_business_analysis(
                loans,
                repayments,
                collections,
                collection_analysis,
            )

        if customer_management is None:
            customer_management, critical_customers = (
                create_customer_management_analysis(
                    customer_analysis,
                    collection_analysis,
                )
            )
        else:
            _, critical_customers = create_customer_management_analysis(
                customer_analysis,
                collection_analysis,
            )

        if product_management is None or risk_management is None:
            product_management, risk_management = create_management_datasets(
                product_summary,
                customer_management,
            )

        if collection_management is None:
            collection_management = create_collection_management_dataset(
                collections
            )

        if executive_kpis is None:
            executive_kpis = create_executive_kpis(
                loan_applications,
                loans,
                repayments,
                collections,
            )

        portfolio_dataset = create_portfolio_dataset(
            loan_risk,
            branches,
            repayments,
            loans,
        )

        credit_risk_dataset, credit_risk_summary = create_credit_risk_dataset(
            customer_analysis
        )

        (
            collection_dataset,
            collection_channel,
            collection_action,
            collection_dpd,
            collection_summary,
        ) = create_final_collection_dataset(collections)

        customer_risk_dataset = create_customer_risk_dataset(
            customer_analysis,
            collections,
        )

        print_dataset_check("EXECUTIVE KPI DATASET", executive_kpis)
        print_dataset_check("PORTFOLIO ANALYSIS DATASET", portfolio_dataset)
        print_dataset_check("CREDIT RISK DATASET", credit_risk_dataset)
        print_dataset_check(
            "COLLECTION PERFORMANCE DATASET",
            collection_dataset,
        )
        print_dataset_check("CUSTOMER RISK DATASET", customer_risk_dataset)
        print_dataset_check(
            "MANAGEMENT PRIORITIES DATASET",
            product_management,
        )

        print_executive_summary(
            executive_kpis,
            critical_customers,
            _high_risk_high_value,
            product_management,
            risk_management,
            collection_management,
        )

        export_analytical_workbook(
            OUTPUT_FILE,
            executive_kpis,
            portfolio_dataset,
            credit_risk_dataset,
            collection_dataset,
            customer_risk_dataset,
            product_management,
        )

        print("\n" + "=" * 70)
        print("FINAL ANALYTICAL WORKBOOK")
        print("=" * 70)
        print("Workbook created successfully.")
        print("File:", OUTPUT_FILE)
        print("\nSheets created:")
        print("1. Executive_KPIs")
        print("2. Portfolio_Analysis")
        print("3. Credit_Risk")
        print("4. Collection_Performance")
        print("5. Customer_Risk")
        print("6. Management_Priorities")


if __name__ == "__main__":
    main()
