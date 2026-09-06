#' ---
#' title: "01_prepare_data.R"
#' description: "Prepare and harmonize NetHealth tie strength and social support data"
#' author: "Omar Lizardo"
#' ---

suppressPackageStartupMessages({
  library(readr)
  library(dplyr)
  library(tidyr)
})

cat("==> Loading raw NetHealth datasets...\n")
raw_dir <- "../identifying-personal-network-types/raw_dat"

net_raw <- read_csv(file.path(raw_dir, "network_survey.csv"), show_col_types = FALSE)
basic_raw <- read_csv(file.path(raw_dir, "basic_survey.csv"), show_col_types = FALSE)

cat("Raw network records:", nrow(net_raw), "\n")
cat("Raw basic survey egos:", nrow(basic_raw), "\n")

# 1. Identify waves with social support and egos who were administered the battery
support_waves <- c("Wave2", "Wave3", "Wave4", "Wave5", "Wave7", "Wave8")

net_supp <- net_raw %>%
  filter(wave %in% support_waves)

# Determine which egos were administered support questions in each wave
# (At least one non-missing response to any support item)
ego_supp_admin <- net_supp %>%
  group_by(wave, egoid) %>%
  summarize(
    supp_administered = any(!is.na(supphang) | !is.na(suppadv) | !is.na(suppcomf) | !is.na(suppfin)),
    .groups = "drop"
  )

net_clean <- net_supp %>%
  inner_join(ego_supp_admin %>% filter(supp_administered), by = c("wave", "egoid"))

cat("Network records for egos administered support battery:", nrow(net_clean), "\n")

# 2. Harmonize Support Variables
# For egos administered the module, unchecked boxes represent FALSE (absence of support)
net_clean <- net_clean %>%
  mutate(
    supp_hang = coalesce(supphang, FALSE),
    supp_adv  = coalesce(suppadv, FALSE),
    supp_comf = coalesce(suppcomf, FALSE),
    supp_fin  = coalesce(suppfin, FALSE),
    supp_count = as.integer(supp_hang) + as.integer(supp_adv) + 
                 as.integer(supp_comf) + as.integer(supp_fin)
  )

# Reconstruct the 5 heuristic categories used in the 2018 Manchester Talk
net_clean <- net_clean %>%
  mutate(
    support_cat5 = case_when(
      supp_hang & supp_adv & supp_comf & supp_fin ~ "Full Support",
      supp_hang & !supp_fin ~ "Hang & Not Fin.",
      (supp_adv | supp_comf) & !supp_hang & !supp_fin ~ "Advice/Comfort",
      supp_fin & !(supp_hang & supp_adv & supp_comf) ~ "Financial Incl.",
      !supp_hang & !supp_adv & !supp_comf & !supp_fin ~ "No Support",
      TRUE ~ "Other"
    ),
    support_cat5 = factor(
      support_cat5,
      levels = c("Full Support", "Hang & Not Fin.", "Advice/Comfort", "Financial Incl.", "No Support")
    )
  )

# 3. Harmonize Tie Strength Indicators
net_clean <- net_clean %>%
  # Filter out ties with missing core strength ratings
  filter(!is.na(close) & !is.na(freq) & !is.na(reltypecat)) %>%
  mutate(
    # Affective Closeness
    close_raw = close,
    close_cat = case_when(
      close == "Distant" ~ "Distant",
      close == "LessThanClose" ~ "Less Close",
      close %in% c("MerelyClose", "Close") ~ "Close",
      close == "EspeciallyClose" ~ "Especially Close",
      TRUE ~ NA_character_
    ),
    close_cat = factor(
      close_cat,
      levels = c("Distant", "Less Close", "Close", "Especially Close")
    ),
    close_num = as.numeric(close_cat),
    is_esp_close = close_cat == "Especially Close",
    
    # Interaction Frequency
    freq_raw = freq,
    freq_cat = case_when(
      freq == "LessThanMonthly" ~ "Less than Monthly",
      freq == "Monthly" ~ "Monthly",
      freq == "Weekly" ~ "Weekly",
      freq == "Daily" ~ "Daily",
      TRUE ~ NA_character_
    ),
    freq_cat = factor(
      freq_cat,
      levels = c("Less than Monthly", "Monthly", "Weekly", "Daily")
    ),
    freq_num = as.numeric(freq_cat),
    is_daily = freq_cat == "Daily",
    
    # Cognitive Salience
    position_num = as.numeric(position),
    pos_cat = case_when(
      position <= 5 ~ "Top 5",
      position <= 15 ~ "Middle 10",
      position <= 20 ~ "Bottom 5",
      TRUE ~ "Other"
    ),
    pos_cat = factor(pos_cat, levels = c("Top 5", "Middle 10", "Bottom 5")),
    is_top5 = position_num <= 5,
    
    # Relationship Duration
    duration_cat = case_when(
      duration %in% c("LessThan1", "1+") ~ "< 2 Years",
      duration %in% c("2+", "3+", "4+") ~ "2-4 Years",
      duration %in% c("5+", "6+", "7+", "8+", "9+", "10+") ~ "5-10 Years",
      duration %in% c("11to12", "13to14", "15to16", "17to18", "19to20", "MoreThan20") ~ "> 10 Years",
      TRUE ~ "Unknown"
    ),
    duration_cat = factor(
      duration_cat,
      levels = c("< 2 Years", "2-4 Years", "5-10 Years", "> 10 Years", "Unknown")
    )
  )

# 4. Harmonize Role Relations
net_clean <- net_clean %>%
  mutate(
    role_cat = case_when(
      reltypecat == "Friend" ~ "Friend",
      reltypecat == "Family" ~ "Family",
      reltypecat == "RomanticPartner" ~ "Romantic Partner",
      reltypecat == "Acquaintance" ~ "Acquaintance",
      reltypecat == "Other" ~ "Other",
      TRUE ~ "Other"
    ),
    role_cat = factor(
      role_cat,
      levels = c("Friend", "Family", "Romantic Partner", "Acquaintance", "Other")
    )
  )

# 5. Link Ego Demographics from basic_survey
ego_demo <- basic_raw %>%
  select(egoid, gender_1, race_1, parentincome_1) %>%
  mutate(
    ego_gender = case_when(
      gender_1 == "Female" ~ "Women",
      gender_1 == "Male" ~ "Men",
      TRUE ~ NA_character_
    ),
    ego_gender = factor(ego_gender, levels = c("Women", "Men")),
    ego_race = case_when(
      race_1 == "White" ~ "White",
      race_1 == "African-American" ~ "Black",
      race_1 == "Asian-American" ~ "Asian",
      race_1 == "Latino/a" ~ "Latino/a",
      race_1 == "Foreign Student" ~ "International",
      !is.na(race_1) ~ "Other",
      TRUE ~ NA_character_
    ),
    ego_race = factor(ego_race, levels = c("White", "Black", "Asian", "Latino/a", "International", "Other"))
  )

net_analytical <- net_clean %>%
  left_join(ego_demo, by = "egoid") %>%
  mutate(
    alter_gender = case_when(
      altsex == "Female" ~ "Women",
      altsex == "Male" ~ "Men",
      TRUE ~ NA_character_
    ),
    alter_gender = factor(alter_gender, levels = c("Women", "Men")),
    gender_homophily = if_else(!is.na(ego_gender) & !is.na(alter_gender), ego_gender == alter_gender, NA),
    same_dorm = coalesce(samedorm, FALSE),
    roommate = coalesce(roommates, FALSE),
    is_wave2_5 = wave %in% c("Wave2", "Wave3", "Wave4", "Wave5"),
    dyad_id = paste(pmin(egoid, alterid), pmax(egoid, alterid), sep = "_")
  )

cat("==> Analytical dataset summary:\n")
cat("Total valid dyad-wave records:", nrow(net_analytical), "\n")
cat("Unique egos:", n_distinct(net_analytical$egoid), "\n")
cat("Unique alters:", n_distinct(net_analytical$alterid), "\n")
cat("Unique dyads:", n_distinct(net_analytical$dyad_id), "\n")
cat("Records in Waves 2-5 (Manchester Talk baseline):", sum(net_analytical$is_wave2_5), "\n")

# Save outputs
saveRDS(net_analytical, "data/tie_support_analytical.rds")
write_csv(net_analytical, "data/tie_support_analytical.csv")
cat("==> Saved data/tie_support_analytical.rds and .csv successfully.\n")
