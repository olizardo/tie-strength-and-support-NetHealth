#' ---
#' title: "02_latent_class_support.R"
#' description: "Latent Class Analysis of social support types in ego networks"
#' author: "Omar Lizardo"
#' ---

suppressPackageStartupMessages({
  library(readr)
  library(dplyr)
  library(tidyr)
  library(poLCA)
  library(ggplot2)
  library(knitr)
})

cat("==> Loading analytical dataset...\n")
df <- readRDS("data/tie_support_analytical.rds")

# Prepare 1/2 binary indicators for poLCA (1 = No, 2 = Yes)
df_lca_input <- df %>%
  transmute(
    hang = as.integer(supp_hang) + 1L,
    adv  = as.integer(supp_adv) + 1L,
    comf = as.integer(supp_comf) + 1L,
    fin  = as.integer(supp_fin) + 1L
  )

f_lca <- cbind(hang, adv, comf, fin) ~ 1

# 1. Fit LCA models across K = 2 to 5 classes
set.seed(12345)
lca_models <- list()
fit_stats <- data.frame(
  Classes = integer(),
  LogLik = numeric(),
  Resid_Df = integer(),
  AIC = numeric(),
  BIC = numeric(),
  Gsq = numeric(),
  Entropy = numeric(),
  stringsAsFactors = FALSE
)

calc_entropy <- function(model) {
  post <- model$posterior
  n <- nrow(post)
  k <- ncol(post)
  # Normalized entropy: 1 - sum(-p * log(p)) / (n * log(k))
  eps <- 1e-12
  post_safe <- pmax(post, eps)
  entropy_val <- 1 + sum(post_safe * log(post_safe)) / (n * log(k))
  return(round(entropy_val, 3))
}

for (k in 2:5) {
  cat(sprintf("Fitting LCA with K = %d classes...\n", k))
  mod <- poLCA(f_lca, df_lca_input, nclass = k, nrep = 3, maxiter = 1000, verbose = FALSE)
  lca_models[[paste0("K_", k)]] <- mod
  
  fit_stats <- rbind(
    fit_stats,
    data.frame(
      Classes = k,
      LogLik = round(mod$llik, 2),
      Resid_Df = mod$resid.df,
      AIC = round(mod$aic, 2),
      BIC = round(mod$bic, 2),
      Gsq = round(mod$Gsq, 3),
      Entropy = calc_entropy(mod),
      stringsAsFactors = FALSE
    )
  )
}

cat("\n==> Model Fit Comparison:\n")
print(fit_stats)
write_csv(fit_stats, "output/tables/lca_fit_statistics.csv")

# 2. Select optimal K = 4 model (lowest BIC and AIC)
best_k <- 4
opt_model <- lca_models[[paste0("K_", best_k)]]

# Extract conditional response probabilities
probs_list <- list()
items <- c("hang", "adv", "comf", "fin")
item_labels <- c(
  "hang" = "Companionship (Hang Out)",
  "adv"  = "Advice / Information",
  "comf" = "Comfort / Emotional",
  "fin"  = "Financial Assistance"
)

for (item in items) {
  p_yes <- as.numeric(opt_model$probs[[item]][, 2])
  probs_list[[item]] <- data.frame(
    class_num = seq_len(best_k),
    item = item,
    item_label = unname(item_labels[item]),
    probability = p_yes,
    stringsAsFactors = FALSE
  )
}

probs_df <- bind_rows(probs_list)

# Determine meaningful class labels based on profile inspection
class_summary <- probs_df %>%
  dplyr::select(class_num, item, probability) %>%
  pivot_wider(names_from = item, values_from = probability) %>%
  mutate(
    class_label = case_when(
      hang > 0.8 & adv > 0.8 & comf > 0.8 ~ "Comprehensive Support",
      hang > 0.8 & adv < 0.6 & comf < 0.5 ~ "Casual Companionship",
      fin > 0.4 & hang < 0.5 ~ "Instrumental / Kin Support",
      TRUE ~ "Low / Peripheral Support"
    )
  )

cat("\n==> Identified Latent Classes:\n")
print(class_summary)

# Merge class labels back to probabilities
probs_df <- probs_df %>%
  left_join(class_summary %>% dplyr::select(class_num, class_label), by = "class_num")

# Plot Conditional Item Response Probabilities (flipped coordinates)
p_lca_profiles <- ggplot(
  probs_df,
  aes(x = item_label, y = probability, fill = class_label, group = class_label)
) +
  geom_col(position = position_dodge(width = 0.8), width = 0.7, color = "black", alpha = 0.85) +
  geom_text(
    aes(label = sprintf("%.2f", probability)),
    position = position_dodge(width = 0.8),
    hjust = -0.15, size = 3.2
  ) +
  coord_flip() +
  scale_y_continuous(
    limits = c(0, 1.15),
    breaks = seq(0, 1, 0.2),
    labels = scales::percent_format(),
    expand = expansion(mult = c(0.01, 0.05))
  ) +
  scale_fill_brewer(palette = "Set2") +
  labs(
    title = "Latent Classes of Social Support Exchanges",
    subtitle = "Item response probabilities from 4-class LCA model (N = 22,739 ties)",
    x = "Support Type",
    y = "Conditional Response Probability",
    fill = "Latent Support Class"
  ) +
  guides(fill = guide_legend(nrow = 2, byrow = TRUE)) +
  theme_minimal(base_size = 11) +
  theme(
    axis.text.y = element_text(face = "bold", color = "black"),
    axis.text.x = element_text(color = "black"),
    legend.position = "bottom",
    legend.title = element_text(face = "bold", size = 10),
    panel.grid.minor = element_blank()
  )

ggsave("output/figures/fig1_lca_support_profiles.png", p_lca_profiles, width = 6.5, height = 4.8, dpi = 300)
ggsave("Plots/fig1_lca_support_profiles.png", p_lca_profiles, width = 6.5, height = 4.8, dpi = 300)
cat("==> Saved output/figures/fig1_lca_support_profiles.png and Plots/fig1_lca_support_profiles.png\n")

# 3. Assign ties to modal latent classes and merge into analytical dataset
class_labels_vec <- setNames(class_summary$class_label, class_summary$class_num)

df_augmented <- df %>%
  mutate(
    lca_class_num = opt_model$predclass,
    lca_class = factor(unname(class_labels_vec[as.character(lca_class_num)]),
      levels = c("Casual Companionship", "Comprehensive Support", "Instrumental / Kin Support", "Low / Peripheral Support")
    ),
    lca_post_prob = apply(opt_model$posterior, 1, max)
  )

# Cross-tabulate Latent Classes with Role Relations and Tie Strength
cat("\n==> Latent Support Classes by Social Role Relation (% within Role):\n")
role_class_tab <- df_augmented %>%
  count(role_cat, lca_class) %>%
  group_by(role_cat) %>%
  mutate(pct = round(100 * n / sum(n), 1)) %>%
  dplyr::select(-n) %>%
  pivot_wider(names_from = lca_class, values_from = pct, values_fill = 0)
print(role_class_tab)
write_csv(role_class_tab, "output/tables/lca_classes_by_role.csv")

cat("\n==> Latent Support Classes by Affective Closeness (% within Closeness):\n")
close_class_tab <- df_augmented %>%
  count(close_cat, lca_class) %>%
  group_by(close_cat) %>%
  mutate(pct = round(100 * n / sum(n), 1)) %>%
  dplyr::select(-n) %>%
  pivot_wider(names_from = lca_class, values_from = pct, values_fill = 0)
print(close_class_tab)
write_csv(close_class_tab, "output/tables/lca_classes_by_closeness.csv")

# Save augmented analytical dataset
saveRDS(df_augmented, "data/tie_support_with_lca.rds")
write_csv(df_augmented, "data/tie_support_with_lca.csv")
saveRDS(opt_model, "data/lca_optimal_model.rds")

cat("==> Latent Class Analysis completed successfully.\n")
