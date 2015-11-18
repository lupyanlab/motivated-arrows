
#' Load the comma-separated data files in a directory.
#'
#' @param data_dir The directory of the data files, passed to `file.path`.
#' @param regex_key Pattern passed to `list.files`. Matches are loaded.
#' @return dplyr::data_frame
#' @export
compile <- function(data_dir, regex_key = "*") {
  data_files <- list.files(data_dir, regex_key, full.names = TRUE)
  plyr::ldply(data_files, readr::read_csv)
}
