export interface BaseFieldProps {
  name: string;
  label?: string;
  help?: string;
  placeholder?: string;
  required?: boolean;
}

export interface Tag {
  name: string;
}

export type TagType = "" | "Event" | "Codebase" | "Job" | "Profile";

export interface RORItem {
  id: string;
  name: string;
  email_address?: string;
  ip_addresses?: any[];
  established?: number | null;
  types: string[];
  relationships: any[];
  addresses: any[];
  links: string[];
  aliases: string[];
  acronyms: string[];
  status: "Active" | "Inactive" | "Withdrawn";
  wikipedia_url?: string;
  labels: string[];
  country: object;
  external_ids: any;
  [key: string | number | symbol]: unknown;
}

export interface Organization {
  name: string;
  url?: string;
  acronym?: string;
  ror_id?: string;
}

export interface TimeSeries {
  name: string;
  data: number[];
  type?: string;
}

export interface Metric {
  title: string;
  yLabel: string;
  startYear: number;
  series: TimeSeries[];
}

export type MetricsData = Record<
  | "startYear"
  | "totalMembers"
  | "fullMembers"
  | "totalCodebases"
  | "codebasesByOs"
  | "codebasesByPlatform"
  | "codebasesByLanguage"
  | "reviewedCodebases"
  | "totalDownloads",
  Metric
>;

export type MetricsChartSelection =
  | "total-members"
  | "full-members"
  | "total-codebases"
  | "reviewed-codebases"
  | "codebases-by-language"
  | "codebases-by-platform"
  | "codebases-by-os"
  | "total-downloads";

export interface ReviewEvent {
  date_created: string;
  action: string;
  message: string;
  author: {
    name: string;
    absolute_url: string;
  };
}

export interface Reviewer {
  id: number;
  name: string;
  avatar_url: string;
  degrees: string[];
  tags: Tag[];
}

export interface CodebaseReleaseEditorState {
  files: CodebaseReleaseFiles;
  release: CodebaseRelease;
}

export interface CodebaseReleaseFiles {
  originals: {
    data: FileInfo[];
    docs: FileInfo[];
    code: FileInfo[];
    results: FileInfo[];
  };
  media: FileInfo[];
}

interface FileInfo {
  name: string;
  identifier: string;
}

export interface License {
  name: string;
  url?: string;
}

interface ReleaseContributor {
  contributor: Contributor;
  include_in_citation?: boolean;
  index?: number;
  profile_url: string;
  roles?: string[];
}

interface Contributor {
  affiliations: any[];
  email: string;
  id: number;
  name: string;
  profile_url?: string;
  type: "person" | "organization";
  user?: {
    institution_name?: string;
    institution_url?: string;
    name: string;
    profile_url: string;
    username: string;
  } | null;
}

export interface LinkedUser {
  name: string;
  profile_url: string;
  username: string;
}

export interface CodebaseRelease {
  absolute_url: string;
  citationText?: string;
  codebase: Codebase;
  date_created: Date;
  dependencies?: any;
  documentation: string | null;
  doi: string | null;
  embargo_end_date: Date | null;
  first_published_at: Date | null;
  identifier: string;
  last_modified: Date | null;
  last_published_on: Date | null;
  license: License | null;
  live: boolean;
  os: string;
  os_display: string;
  peer_reviewed: boolean;
  platforms: Tag[];
  possible_licenses: License[];
  programming_languages: Tag[];
  release_contributors: ReleaseContributor[];
  release_notes: string;
  review_status: string | null;
  share_url: string | null;
  submitted_package: string | null;
  submitter: LinkedUser;
  urls: {
    request_peer_review: string | null;
    review: string | null;
    notify_reviewers_of_changes: string | null;
  };
  version_number: string;
}

interface Codebase {
  absolute_url: string;
  all_contributors: Contributor[];
  associated_publication_text?: string;
  date_created: Date;
  description: string;
  doi?: string | null;
  download_count: number;
  featured_image: string | null;
  first_published_at: Date | null;
  id: number;
  identifier: string;
  last_published_on: Date | null;
  latest_version_number?: string;
  peer_reviewed?: boolean;
  references_text?: string;
  releases?: any[];
  replication_text?: string;
  repository_url?: string;
  submitter: LinkedUser;
  summarized_description: string;
  tags: Tag[];
  title: string;
}

export type CodebaseReleaseMetadata = Pick<
  CodebaseRelease,
  | "release_notes"
  | "embargo_end_date"
  | "os"
  | "platforms"
  | "programming_languages"
  | "live"
  | "license"
>;
