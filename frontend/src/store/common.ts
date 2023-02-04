import * as _ from "lodash";

export interface UndefinedWithId {
  id?: number;
}

export interface User {
  family_name: string;
  given_name: string;
  username: string;
}

export interface Job extends UndefinedWithId {
  title: string;
  tags: Array<{ name: string }>;
  summary: string;
  submitter?: User;
  description: string;
}

export interface CalendarEvent extends UndefinedWithId {
  description: string;
  early_registration_deadline: string;
  end_date: string;
  location: string;
  start_date: string;
  submission_deadline: string;
  submitter?: User;
  summary: string;
  tags: string[];
  title: string;
}

export interface MemberProfile extends UndefinedWithId {
  bio: string;
  codebases: Codebase[];
  date_joined: string;
  degrees: string[];
  family_name: string;
  follower_count: number;
  following_count: number;
  full_member: boolean;
  given_name: string;
  affiliations: Array<{ name: string; url?: string; acronym?: string; ror_id?: string }>;
  keywords: Array<{ name: string }>;
  orcid: string;
  orcid_url: string;
  personal_url: string;
  picture: string;
  professional_url: string;
  profile_url: string;
  research_interests: string;
  username: string;
}

interface RelatedMemberProfile {
  name: string;
  institution_name: string;
  institution_url: string;
  profile_url: string;
  username: string | null;
}

export interface Contributor {
  affiliations: string[];
  email: string;
  given_name: string;
  middle_name: string;
  family_name: string;
  type: string;
  user: RelatedMemberProfile;
  valid?: boolean; // is this property exists display an error
}

export const emptyContributor = (valid: boolean = false): Contributor => {
  return {
    affiliations: [],
    email: "",
    given_name: "",
    middle_name: "",
    family_name: "",
    type: "person",
    user: {
      name: "",
      institution_name: "",
      institution_url: "",
      profile_url: "",
      username: null,
    },
    valid,
  };
};

export interface CodebaseContributor {
  _id: string;
  roles: string[];
  contributor: Contributor;
}

export const emptyReleaseContributor = (): CodebaseContributor => {
  return {
    _id: _.uniqueId(),
    roles: ["author"],
    contributor: emptyContributor(),
  };
};

interface AbstractCodebase extends UndefinedWithId {
  associatiated_publications_text: string;
  description: string;
  doi: string | null;
  featured: boolean;
  first_published_on: string;
  has_published_changes: boolean;
  identifier: string;
  is_replication: boolean;
  keywords: string[];
  last_published_on: string;
  latest_version: string | null;
  live: boolean;
  peer_reviewed: boolean;
  references_text: string;
  relationships: object;
  repository_url: string;
  submitter: User;
  summary: string;
  tags: Array<{ name: string }>;
  title: string;
}

export interface Codebase extends AbstractCodebase {
  all_contributors: object[];
  releases: CodebaseRelease[];
}

export interface CodebaseEdit extends AbstractCodebase {}

export interface Dependency {
  identifier: string;
  name: string;
  os: string;
  url: string;
  version: string;
}

// codebase_contributors, dependencies, description, documentation, doi, download_count, enbargo_end_date, license, os, peer_reviewed, platforms, programming_languages, submitted_package, submitter, version_number
interface AbstractCodebaseRelease extends UndefinedWithId {
  absolute_url: string;
  release_contributors: CodebaseContributor[];
  dependencies: Dependency[];
  documentation: string;
  doi: string | null;
  embargo_end_date: string | null;
  license: string;
  live: boolean;
  identifier: string;
  os: string;
  peer_reviewed: boolean;
  platforms: Array<{ name: string }>;
  possible_licenses: Array<{ name: string; url: string }>;
  programming_languages: Array<{ name: string }>;
  release_notes: string;
  review_status: string | null;
  submitted_package: string;
  submitter: User;
  version_number: string;
  urls: {
    request_peer_review: string | null;
    review: string | null;
    notify_reviewers_of_changes: string | null;
  };
}

export interface CodebaseRelease extends AbstractCodebaseRelease {
  codebase?: number;
}

export interface CodebaseReleaseEdit extends AbstractCodebaseRelease {
  codebase: CodebaseEdit;
}

interface FileInfo {
  name: string;
  identifier: string;
}

interface CodebaseReleaseFileLayout<T> {
  data: T[];
  docs: T[];
  code: T[];
  results: T[];
}

export interface CodebaseReleaseStore {
  files: {
    originals: CodebaseReleaseFileLayout<FileInfo>;
    media: FileInfo[];
  };
  release: CodebaseReleaseEdit;
}

export interface StatusMessages {
  errors: string[];
  warnings: string[];
  successes: string[];
}
