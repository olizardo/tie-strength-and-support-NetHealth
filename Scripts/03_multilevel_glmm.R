#' ---
#' title: "03_multilevel_glmm.R"
#' description: "Multilevel Generalized Linear Mixed Models (GLMM) predicting LCA Support Categories"
#' author: "Omar Lizardo"
#' ---

suppressPackageStartupMessages({
  library(readr)
  library(dplyr)
  library(tidyr)
  library(lme4)
  library(ggplot2)
})

cat("==> Loading data with latent classes...\n")
df <- readRDS("data/tie_support_with_lca.rds") %>%
  filter(!is.na(ego_gender) & !is.na(close_cat) & !is.na(freq_cat) & !is.na(role_cat) & duration_cat != "Unknown") %>%
  mutate(
    # Set standard reference categories
    close_cat = relevel(close_cat, ref = "Close"),
    freq_cat = relevel(freq_cat, ref = "Weekly"),
    pos_cat = relevel(pos_cat, ref = "Middle 10"),
    duration_cat = relevel(duration_cat, ref = "2-4 Years"),
    role_cat = relevel(role_cat, ref = "Friend"),
    supp_comp = as.integer(lca_class == "Comprehensive Support"),
    supp_cas  = as.integer(lca_class == "Casual Companionship"),
    supp_inst = as.integer(lca_class == "Instrumental Support"),
    supp_per  = as.integer(lca_class == "Peripheral Support")
  )

cat("Analytical sample size for GLMMs:", nrow(df), "ties across", n_distinct(df$egoid), "egos.\n")

# Formula specification for GLMM predicting each latent class
outcomes <- c(
  "supp_comp" = "Comprehensive Support",
  "supp_cas"  = "Casual Companionship",
  "supp_inst" = "Instrumental Support",
  "supp_per"  = "Peripheral Support"
)

models <- list()
tidy_list <- list()

for (outcome in names(outcomes)) {
  outcome_label <- outcomes[outcome]
  cat(sprintf("\n==> Fitting Multilevel GLMM for Latent Support Class: %s...\n", outcome_label))
  
  f <- as.formula(paste(
    outcome,
    "~ close_cat + freq_cat + pos_cat + duration_cat + role_cat + ego_gender + same_dorm + roommate + (1 | egoid)"
  ))
  
  mod <- glmer(
    f,
    data = df,
    family = binomial,
    nAGQ = 0
  )
  
  models[[outcome]] <- mod
  s_mod <- summary(mod)
  c_tab <- s_mod$coefficients
  
  td <- data.frame(
    term = rownames(c_tab),
    estimate_log_odds = c_tab[, 1],
    std_error = c_tab[, 2],
    z_value = c_tab[, 3],
    p_value = c_tab[, 4],
    estimate = exp(c_tab[, 1]),
    conf_low = exp(c_tab[, 1] - 1.96 * c_tab[, 2]),
    conf_high = exp(c_tab[, 1] + 1.96 * c_tab[, 2]),
    outcome = outcome,
    outcome_label = outcome_label,
    stringsAsFactors = FALSE
  )
  
  # Extract random intercept variance
  ran_var <- as.data.frame(VarCorr(mod))$vcov[1]
  icc <- ran_var / (ran_var + (pi^2 / 3))
  cat(sprintf("  Ego random intercept variance: %.3f (Latent ICC: %.3f)\n", ran_var, icc))
  
  tidy_list[[outcome]] <- td
}

all_tidy <- bind_rows(tidy_list)

# Clean predictor labels for reporting
all_tidy <- all_tidy %>%
  mutate(
    term_clean = case_when(
      term == "(Intercept)" ~ "Intercept",
      term == "close_catDistant" ~ "Closeness: Distant (vs. Close)",
      term == "close_catLess Close" ~ "Closeness: Less Close (vs. Close)",
      term == "close_catEspecially Close" ~ "Closeness: Especially Close (vs. Close)",
      term == "freq_catLess than Monthly" ~ "Frequency: Less than Monthly (vs. Weekly)",
      term == "freq_catMonthly" ~ "Frequency: Monthly (vs. Weekly)",
      term == "freq_catDaily" ~ "Frequency: Daily (vs. Weekly)",
      term == "pos_catTop 5" ~ "Salience: Top 5 (vs. Middle 10)",
      term == "pos_catBottom 5" ~ "Salience: Bottom 5 (vs. Middle 10)",
      term == "duration_cat< 2 Years" ~ "Duration: < 2 Years (vs. 2-4 Years)",
      term == "duration_cat5-10 Years" ~ "Duration: 5-10 Years (vs. 2-4 Years)",
      term == "duration_cat> 10 Years" ~ "Duration: > 10 Years (vs. 2-4 Years)",
      term == "role_catFamily" ~ "Role: Family (vs. Friend)",
      term == "role_catRomantic Partner" ~ "Role: Romantic Partner (vs. Friend)",
      term == "role_catAcquaintance" ~ "Role: Acquaintance (vs. Friend)",
      term == "role_catOther" ~ "Role: Other (vs. Friend)",
      term == "ego_genderMen" ~ "Ego Gender: Men (vs. Women)",
      term == "same_dormTRUE" ~ "Context: Same Dormitory",
      term == "roommateTRUE" ~ "Context: Roommate",
      TRUE ~ term
    )
  )

write_csv(all_tidy, "output/tables/glmm_results_odds_ratios.csv")
saveRDS(models, "data/glmm_fitted_models.rds")
cat("==> Saved output/tables/glmm_results_odds_ratios.csv and data/glmm_fitted_models.rds\n")

# Forest Plot of Key Predictors across Latent Support Classes
core_terms <- c(
  "Closeness: Especially Close (vs. Close)",
  "Closeness: Less Close (vs. Close)",
  "Frequency: Daily (vs. Weekly)",
  "Frequency: Monthly (vs. Weekly)",
  "Salience: Top 5 (vs. Middle 10)",
  "Role: Family (vs. Friend)",
  "Role: Romantic Partner (vs. Friend)",
  "Role: Acquaintance (vs. Friend)",
  "Context: Same Dormitory",
  "Ego Gender: Men (vs. Women)"
)

plot_df <- all_tidy %>%
  filter(
    term_clean %in% core_terms
  ) %>%
  mutate(
    term_clean = factor(term_clean, levels = rev(core_terms)),
    outcome_label = factor(
      outcome_label,
      levels = c("Comprehensive Support", "Casual Companionship", "Instrumental Support", "Peripheral Support")
    )
  )

p_forest <- ggplot(plot_df, aes(x = estimate, y = term_clean, color = outcome_label)) +
  geom_vline(xintercept = 1, linetype = "dashed", color = "gray50") +
  geom_pointrange(
    aes(xmin = conf_low, xmax = conf_high),
    position = position_dodge(width = 0.65),
    linewidth = 0.5,
    size = 0.4
  ) +
  scale_x_log10(breaks = c(0.1, 0.2, 0.5, 1, 2, 5, 10, 20)) +
  scale_color_brewer(palette = "Set2") +
  labs(
    title = "Predictors of Latent Social Support Configurations Across Ego Networks",
    subtitle = "Multilevel Logistic GLMM Odds Ratios with 95% Confidence Intervals (N = 22,737 ties)",
    x = "Adjusted Odds Ratio (log scale)",
    y = NULL,
    color = "Latent Support Class"
  ) +
  guides(color = guide_legend(nrow = 2, byrow = TRUE)) +
  theme_minimal(base_size = 11) +
  theme(
    legend.position = "bottom",
    panel.grid.minor = element_blank(),
    axis.text.y = element_text(face = "bold", color = "black"),
    axis.text.x = element_text(color = "black")
  )

ggsave("output/figures/fig2_glmm_odds_ratios.png", p_forest, width = 6.5, height = 5.2, dpi = 300)
ggsave("Plots/fig2_glmm_odds_ratios.png", p_forest, width = 6.5, height = 5.2, dpi = 300)
cat("==> Saved output/figures/fig2_glmm_odds_ratios.png and Plots/fig2_glmm_odds_ratios.png\n")
