library(magrittr)

longest_text <- function(xs) {
  lens <- purrr::map_dbl(xs, stringr::str_length)
  maxind <- which.max(lens)
  maxind <- ifelse(length(maxind) == 0, 1, maxind)
  xs[maxind]
}

agg <- function(x, y, f, default) {
  f(x[order(y)])
}

df <- readr::read_csv("/shared/statistics/members.csv")

duplicated_accounts <- df %>%
  dplyr::filter(!is.na(last_name)) %>%
  dplyr::filter(!is.na(first_name)) %>%
  dplyr::arrange(last_name, first_name) %>%
  dplyr::mutate(
    last_name = stringr::str_to_lower(last_name),
    first_name = stringr::str_to_lower(first_name)) %>%
  dplyr::group_by(last_name, first_name) %>%
  dplyr::summarise(n = dplyr::n(), emails = jsonlite::toJSON(purrr::compact(email))) %>%
  dplyr::filter(n > 1)

readr::write_csv(duplicated_accounts, '/shared/statistics/duplicated_accounts.csv')

all_accounts <- df %>%
  dplyr::filter(!is.na(last_name)) %>%
  dplyr::filter(!is.na(first_name)) %>%
  dplyr::mutate(
    last_name = stringr::str_to_lower(last_name),
    first_name = stringr::str_to_lower(first_name)) %>%
  dplyr::group_by(last_name, first_name) %>%
  dplyr::arrange(desc(date_joined)) %>%
  dplyr::summarize(
    email = dplyr::first(email),
    all_emails = jsonlite::toJSON(purrr::compact(email)),
    date_joined = dplyr::first(date_joined),
    bio = longest_text(bio),
    institution = longest_text(institution),
    degrees = longest_text(degrees),
    orcid_url = longest_text(orcid_url),
    github_url = longest_text(github_url),
    research_interests = longest_text(research_interests),
    affiliations = longest_text(affiliations)) %>%
  dplyr::union_all(
    df %>%
      dplyr::mutate(all_emails = jsonlite::toJSON(list())) %>%
      dplyr::filter(is.na(last_name) | is.na(first_name)) %>%
      dplyr::mutate(
        last_name = stringr::str_to_lower(last_name),
        first_name = stringr::str_to_lower(first_name)))

readr::write_csv(all_accounts, '/shared/statistics/all_accounts.csv')

# need to decide what to save for reporting purposes here
                