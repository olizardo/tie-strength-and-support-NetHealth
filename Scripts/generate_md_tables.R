#' ---
#' title: "generate_md_tables.R"
#' description: "Generate standardized markdown tables for APA injection"
#' author: "Omar Lizardo"
#' ---

suppressPackageStartupMessages({
  library(dplyr)
  library(readr)
})

cat("==> Generating markdown tables in cache/...\n")

# -------------------------------------------------------------
# Table 1: LCA Model Fit Comparison
# -------------------------------------------------------------
lca_fit <- read_csv("output/tables/lca_fit_statistics.csv", show_col_types = FALSE)

t1_lines <- c(
  "| Latent Classes | Log-Likelihood | Par | AIC | BIC | Entropy |",
  "|:---|:---:|:---:|:---:|:---:|:---:|",
  sprintf("| %d Classes | %s | %d | %s | %s | %.3f |",
          lca_fit$Classes,
          format(round(lca_fit$LogLik, 1), big.mark = ","),
          c(9, 14, 19, 24)[1:nrow(lca_fit)],
          format(round(lca_fit$AIC, 1), big.mark = ","),
          format(round(lca_fit$BIC, 1), big.mark = ","),
          lca_fit$Entropy)
)
writeLines(t1_lines, "cache/table1_lca_fit.md")
cat("Generated cache/table1_lca_fit.md\n")

# -------------------------------------------------------------
# Table 2: Latent Support Class Distribution by Role and Closeness
# -------------------------------------------------------------
role_tab <- read_csv("output/tables/lca_classes_by_role.csv", show_col_types = FALSE)
close_tab <- read_csv("output/tables/lca_classes_by_closeness.csv", show_col_types = FALSE)

t2_lines <- c(
  "| Dimension & Category | Casual Companionship | Comprehensive Support | Instrumental / Kin | Low / Peripheral |",
  "|:---|:---:|:---:|:---:|:---:|",
  "| **Panel A: Social Role Relation** | | | | |",
  sprintf("| &nbsp;&nbsp;Friend | %.1f%% | %.1f%% | %.1f%% | %.1f%% |",
          role_tab$`Casual Companionship`[role_tab$role_cat == "Friend"],
          role_tab$`Comprehensive Support`[role_tab$role_cat == "Friend"],
          role_tab$`Instrumental / Kin Support`[role_tab$role_cat == "Friend"],
          role_tab$`Low / Peripheral Support`[role_tab$role_cat == "Friend"]),
  sprintf("| &nbsp;&nbsp;Family | %.1f%% | %.1f%% | %.1f%% | %.1f%% |",
          role_tab$`Casual Companionship`[role_tab$role_cat == "Family"],
          role_tab$`Comprehensive Support`[role_tab$role_cat == "Family"],
          role_tab$`Instrumental / Kin Support`[role_tab$role_cat == "Family"],
          role_tab$`Low / Peripheral Support`[role_tab$role_cat == "Family"]),
  sprintf("| &nbsp;&nbsp;Romantic Partner | %.1f%% | %.1f%% | %.1f%% | %.1f%% |",
          role_tab$`Casual Companionship`[role_tab$role_cat == "Romantic Partner"],
          role_tab$`Comprehensive Support`[role_tab$role_cat == "Romantic Partner"],
          role_tab$`Instrumental / Kin Support`[role_tab$role_cat == "Romantic Partner"],
          role_tab$`Low / Peripheral Support`[role_tab$role_cat == "Romantic Partner"]),
  sprintf("| &nbsp;&nbsp;Acquaintance | %.1f%% | %.1f%% | %.1f%% | %.1f%% |",
          role_tab$`Casual Companionship`[role_tab$role_cat == "Acquaintance"],
          role_tab$`Comprehensive Support`[role_tab$role_cat == "Acquaintance"],
          role_tab$`Instrumental / Kin Support`[role_tab$role_cat == "Acquaintance"],
          role_tab$`Low / Peripheral Support`[role_tab$role_cat == "Acquaintance"]),
  sprintf("| &nbsp;&nbsp;Other Role | %.1f%% | %.1f%% | %.1f%% | %.1f%% |",
          role_tab$`Casual Companionship`[role_tab$role_cat == "Other"],
          role_tab$`Comprehensive Support`[role_tab$role_cat == "Other"],
          role_tab$`Instrumental / Kin Support`[role_tab$role_cat == "Other"],
          role_tab$`Low / Peripheral Support`[role_tab$role_cat == "Other"]),
  "| **Panel B: Emotional Closeness** | | | | |",
  sprintf("| &nbsp;&nbsp;Distant | %.1f%% | %.1f%% | %.1f%% | %.1f%% |",
          close_tab$`Casual Companionship`[close_tab$close_cat == "Distant"],
          close_tab$`Comprehensive Support`[close_tab$close_cat == "Distant"],
          close_tab$`Instrumental / Kin Support`[close_tab$close_cat == "Distant"],
          close_tab$`Low / Peripheral Support`[close_tab$close_cat == "Distant"]),
  sprintf("| &nbsp;&nbsp;Less Close | %.1f%% | %.1f%% | %.1f%% | %.1f%% |",
          close_tab$`Casual Companionship`[close_tab$close_cat == "Less Close"],
          close_tab$`Comprehensive Support`[close_tab$close_cat == "Less Close"],
          close_tab$`Instrumental / Kin Support`[close_tab$close_cat == "Less Close"],
          close_tab$`Low / Peripheral Support`[close_tab$close_cat == "Less Close"]),
  sprintf("| &nbsp;&nbsp;Close | %.1f%% | %.1f%% | %.1f%% | %.1f%% |",
          close_tab$`Casual Companionship`[close_tab$close_cat == "Close"],
          close_tab$`Comprehensive Support`[close_tab$close_cat == "Close"],
          close_tab$`Instrumental / Kin Support`[close_tab$close_cat == "Close"],
          close_tab$`Low / Peripheral Support`[close_tab$close_cat == "Close"]),
  sprintf("| &nbsp;&nbsp;Especially Close | %.1f%% | %.1f%% | %.1f%% | %.1f%% |",
          close_tab$`Casual Companionship`[close_tab$close_cat == "Especially Close"],
          close_tab$`Comprehensive Support`[close_tab$close_cat == "Especially Close"],
          close_tab$`Instrumental / Kin Support`[close_tab$close_cat == "Especially Close"],
          close_tab$`Low / Peripheral Support`[close_tab$close_cat == "Especially Close"])
)
writeLines(t2_lines, "cache/table2_lca_crosstabs.md")
cat("Generated cache/table2_lca_crosstabs.md\n")

# -------------------------------------------------------------
# Table 3: Multilevel GLMM Estimates (Odds Ratios and CIs)
# -------------------------------------------------------------
glmm_res <- read_csv("output/tables/glmm_results_odds_ratios.csv", show_col_types = FALSE)

# Select key terms
terms_order <- c(
  "close_catEspecially Close" = "Closeness: Especially Close (ref: Close)",
  "close_catLess Close" = "Closeness: Less Close",
  "close_catDistant" = "Closeness: Distant",
  "freq_catDaily" = "Frequency: Daily (ref: Weekly)",
  "freq_catMonthly" = "Frequency: Monthly",
  "freq_catLess than Monthly" = "Frequency: Less than Monthly",
  "pos_catTop 5" = "Cognitive Salience: Top 5 (ref: Mid 10)",
  "pos_catBottom 5" = "Cognitive Salience: Bottom 5",
  "duration_cat5-10 Years" = "Duration: 5-10 Years (ref: 2-4 Years)",
  "duration_cat> 10 Years" = "Duration: > 10 Years",
  "role_catFamily" = "Role: Family (ref: Friend)",
  "role_catRomantic Partner" = "Role: Romantic Partner",
  "role_catAcquaintance" = "Role: Acquaintance",
  "role_catOther" = "Role: Other Role",
  "same_dormTRUE" = "Context: Same Dormitory",
  "roommateTRUE" = "Context: Roommate",
  "ego_genderMen" = "Ego Gender: Men (ref: Women)"
)

# Build table across outcomes: supp_hang, supp_adv, supp_comf, supp_fin
format_cell <- function(sub_df, trm) {
  row <- sub_df %>% filter(term == trm)
  if (nrow(row) == 0) return("-")
  est <- row$estimate[1]
  p <- row$p_value[1]
  sig <- if (p < 0.001) "***" else if (p < 0.01) "**" else if (p < 0.05) "*" else ""
  sprintf("%.2f%s (%.2f, %.2f)", est, sig, row$conf_low[1], row$conf_high[1])
}

hang_df <- glmm_res %>% filter(outcome == "supp_hang")
adv_df  <- glmm_res %>% filter(outcome == "supp_adv")
comf_df <- glmm_res %>% filter(outcome == "supp_comf")
fin_df  <- glmm_res %>% filter(outcome == "supp_fin")

t3_lines <- c(
  "| Predictor Variable | Companionship OR (95% CI) | Advice OR (95% CI) | Comfort OR (95% CI) | Financial OR (95% CI) |",
  "|:---|:---:|:---:|:---:|:---:|",
  sapply(names(terms_order), function(trm) {
    lbl <- terms_order[trm]
    sprintf("| %s | %s | %s | %s | %s |",
            lbl,
            format_cell(hang_df, trm),
            format_cell(adv_df, trm),
            format_cell(comf_df, trm),
            format_cell(fin_df, trm))
  }, USE.NAMES = FALSE)
)
writeLines(t3_lines, "cache/table3_glmm_models.md")
cat("Generated cache/table3_glmm_models.md\n")
