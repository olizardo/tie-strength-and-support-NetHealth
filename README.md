# Tie Strength and Social Support in Ego Networks (NetHealth)

This repository recreates, updates, and expands the research project presented in **Omar Lizardo's** 2018 Manchester Seminar (*"Tie strength, role relations, and social support in ego networks"*, University of Manchester). 

The project investigates how multidimensional indicators of tie strength (emotional closeness, contact frequency, cognitive salience, and duration) relate to social role relations (family, friends, romantic partners, acquaintances) and the provision of distinct types of social support in egocentric networks.

---

## Moving Beyond Log-Linear Models

The original 2018 analysis utilized multi-way log-linear contingency table models on pooled tie records and manually binned support categories. This updated project advances the empirical framework in several fundamental ways:

1. **Latent Class Analysis (LCA)**:
   - Instead of imposing arbitrary Boolean rules to group support types, we estimate latent class models (`poLCA`) across four primary support indicators (hanging out/companionship, advice, emotional comfort, and financial support) across $K = 2 \dots 6$ classes.
   - We identify five empirical support configurations:
     - *Full Multi-Domain Support* (all support types)
     - *Companionship & Expressive Support* (hanging out + advice + comfort, no financial)
     - *Expressive Support Only* (advice + comfort)
     - *Companionship Only* (hanging out)
     - *Low / No Support*

2. **Multilevel Generalized Linear Mixed Models (GLMMs)**:
   - Dyadic ties are nested within egos across longitudinal waves. We fit multilevel logistic GLMMs (`lme4::glmer`) with random ego intercepts (`(1 | egoid)`) to correctly partition within-ego from between-ego variance and prevent standard error deflation.
   - We independently test how emotional closeness, interaction frequency, cognitive salience (name order rank), and relationship duration predict specific support outcomes, controlling for role relations and ego/alter demographics.

---

## Repository Structure

```
├── Manchester Talk.pptx        # Original 2018 presentation slides
├── data/                       # Analytical data and fitted models (.gitignore protected)
│   └── .gitkeep
├── output/
│   ├── figures/                # Publication-quality visualizations (PNG)
│   │   ├── fig1_lca_support_profiles.png
│   │   └── fig2_glmm_odds_ratios.png
│   └── tables/                 # Summary tables and model estimates (CSV)
│       ├── lca_fit_statistics.csv
│       ├── lca_classes_by_role.csv
│       ├── lca_classes_by_closeness.csv
│       └── glmm_results_odds_ratios.csv
└── Scripts/
    ├── 01_prepare_data.R       # Data ingestion, harmonization, and tie variable coding
    ├── 02_latent_class_support.R # poLCA estimation, model fit comparison, and profile plotting
    └── 03_multilevel_glmm.R    # Mixed-effects logistic regression models predicting support
```

---

## Data Requirements and Setup

The analytical pipeline uses ego-network survey files from the **NetHealth** longitudinal study:
- `network_survey.csv`: Ego-alter tie records across waves (name generators and interpreters).
- `basic_survey.csv`: Ego-level demographic and health survey data.

By default, the scripts look for raw files in `../identifying-personal-network-types/raw_dat/` or a local `raw_dat/` directory. Due to participant privacy and IRB constraints, raw microdata files are excluded from version control.

---

## Replication Pipeline

To replicate the complete analysis from scratch:

```bash
# 1. Clean and harmonize network tie records across waves
Rscript Scripts/01_prepare_data.R

# 2. Estimate latent class models and generate support profile figures
Rscript Scripts/02_latent_class_support.R

# 3. Fit multilevel GLMMs and export odds-ratio summary tables and plots
Rscript Scripts/03_multilevel_glmm.R
```

---

## Key Substantive Findings

1. **Divergence of Closeness and Frequency**:
   - Emotional closeness and contact frequency represent distinct dimensions of tie strength rather than interchangeable indicators.
   - Family ties maintain high emotional closeness and broad support provision despite lower everyday activation frequency compared to campus friends.

2. **Support Specialization by Role Relation**:
   - Financial assistance is heavily concentrated in family ties (and romantic partners), virtually absent among casual friends and acquaintances regardless of interaction frequency.
   - Companionship and emotional support are strongly driven by daily interaction frequency and emotional closeness within friend ties.

3. **Multilevel GLMM Effects**:
   - Net of role relations and ego-level clustering, emotional closeness is the single strongest predictor of emotional comfort and advice, whereas daily contact frequency primarily drives companionship and socializing.
