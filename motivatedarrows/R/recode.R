#' Recode all variables for this experiment.
#'
#' @param frame data.frame to recode.
#' @importFrom dplyr `%>%`
#' @export
recode <- function(frame) {
  frame %>%
    recode_cue_type %>%
    recode_cue_validity
}

recode_cue_type <- function(frame) {
  cue_type_map <- dplyr::data_frame(
    cue_type = c("arrow", "word"),
    cue_c = c(-0.5, 0.5)
  )
  try(frame <- dplyr::left_join(frame, cue_type_map))
  frame
}

recode_cue_validity <- function(frame) {
  cue_validity_map <- dplyr::data_frame(
    cue_validity = c("invalid", "valid"),
    validity_c = c(-0.5, 0.5)
  )
  try(frame <- dplyr::left_join(frame, cue_validity_map))
  frame
}

add_sig_stars <- function(frame) {
  frame %>% mutate(
    sig = ifelse(p.value > 0.05, "",
                 ifelse(p.value > 0.01, "*",
                        ifelse(p.value > 0.001, "**",
                               "***"))))
}
