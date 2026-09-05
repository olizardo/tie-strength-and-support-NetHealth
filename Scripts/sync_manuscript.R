#!/usr/bin/env Rscript
# Scripts/sync_manuscript.R
# Master driver script to synchronize figures, APA tables, and narrative updates directly with Google Drive / Docs

suppressPackageStartupMessages({
  library(googledrive)
})

main <- function() {
  args <- commandArgs(trailingOnly = TRUE)
  from_markdown <- "--from-markdown" %in% args

  doc_id <- "1WdwlqAfHRr7J6rb21Ri6Iq2Iay8lFFTTtqCaBEZznb0"
  live_docx <- "draft_live.docx"
  updated_docx <- "draft_updated.docx"

  on.exit({
    unlink(Sys.glob("draft_*.docx"))
    unlink(Sys.glob("draft_*.txt"))
    unlink(Sys.glob("*.tmp"))
    unlink("replacements.json")
  }, add = TRUE)

  message("[1/4] Ensuring analytical pipeline tables in cache/ are up to date...")
  if (file.exists("Scripts/generate_md_tables.R")) {
    source("Scripts/generate_md_tables.R")
  }

  message("[2/4] Authenticating with Google Drive...")
  drive_auth(email = "omarlizardo@gmail.com")

  if (from_markdown) {
    message("Compiling base manuscript from draft_manuscript.md...")
    system2("pandoc", args = c("draft_manuscript.md", "-o", live_docx))
  } else {
    message("Downloading live manuscript from Google Drive...")
    drive_download(as_id(doc_id), path = live_docx, overwrite = TRUE)
  }

  message("[3/4] Performing in-place OpenXML injection of APA tables and figures...")
  exit_code <- system2("python3", args = c("Scripts/sync_manuscript.py", live_docx, updated_docx))
  if (exit_code != 0) {
    stop("Error during in-place OpenXML injection.")
  }

  message("[4/4] Uploading updated manuscript back to Google Drive...")
  drive_update(as_id(doc_id), media = updated_docx)

  message("====================================================================")
  message("Synchronization complete! Manuscript successfully published to Google Drive.")
  message(paste0("Document URL: https://docs.google.com/document/d/", doc_id))
  message("====================================================================")
}

main()
