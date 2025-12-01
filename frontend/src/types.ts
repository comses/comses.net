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

type NonEmptyArray<T> = [T, ...T[]];

export interface RORLocation {
  geonames_id: number;
  geonames_details: {
    name: string;
    lat?: number | null;
    lng?: number | null;
    country_code?: string | null;
    country_name?: string | null;
  };
}
export interface RORItem {
  admin: {
    created: {
      date: string;
      schema_version: "1.0" | "2.0";
    };
    last_modified: {
      date: string;
      schema_version: "1.0" | "2.0";
    };
  };
  domains?: string[];
  established?: null | number;
  external_ids?: {
    all: string[];
    type: "fundref" | "grid" | "isni" | "wikidata";
    preferred?: string | null;
  }[];
  id: string;
  links?: {
    value: string;
    type: "website" | "wikipedia";
  }[];
  locations: NonEmptyArray<RORLocation>;
  names: NonEmptyArray<{
    value: string;
    types: NonEmptyArray<"acronym" | "alias" | "label" | "ror_display">;
    lang?: string | null;
  }>;
  relationships?: {
    type: "related" | "parent" | "child" | "successor" | "predecessor";
    id: string;
    label: string;
  }[];
  status: "active" | "inactive" | "withdrawn";
  types: NonEmptyArray<
    | "education"
    | "funder"
    | "healthcare"
    | "company"
    | "archive"
    | "nonprofit"
    | "government"
    | "facility"
    | "other"
  >;
}

export interface Organization {
  name: string;
  rorId?: string;
  aliases?: string[];
  acronyms?: string[];
  url?: string;
  link?: string;
  types?: RORItem["types"];
  wikipediaUrl?: string;
  wikidata?: string[];
  coordinates?: {
    lat: number;
    lon: number;
  };
  location?: RORLocation;
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

export type InstitutionMetric = {
  name: string;
  lat: number;
  lon: number;
  value: number;
};

export type MetricsData = Record<
  | "startYear"
  | "totalMembers"
  | "fullMembers"
  | "totalModels"
  | "totalReleases"
  | "reviewedReleases"
  | "releasesByOs"
  | "releasesByPlatform"
  | "releasesByLanguage"
  | "reviewedModels"
  | "totalDownloads",
  Metric
> & {
  institutionData: InstitutionMetric[];
};

export type MetricsChartSelection =
  | "total-members"
  | "full-members"
  | "total-models"
  | "total-releases"
  | "reviewed-releases"
  | "reviewed-models"
  | "releases-by-language"
  | "releases-by-platform"
  | "releases-by-os"
  | "total-downloads";

export interface ReviewEvent {
  dateCreated: string;
  action: string;
  message: string;
  author: {
    name: string;
    absoluteUrl: string;
  };
}

export interface Reviewer {
  id: number;
  isActive: boolean;
  memberProfile: RelatedMemberProfile;
  memberProfileId: number;
  programmingLanguages: string[];
  subjectAreas: string[];
  notes: string;
}

export interface ReviewerFeedback {
  id: number;
  dateCreated: string;
  lastModified: string;
  invitation: number;
  recommendation?: "revise" | "accept";
  privateReviewerNotes: string;
  privateEditorNotes: string;
  notesToAuthor: string;
  hasNarrativeDocumentation: boolean;
  narrativeDocumentationComments: string;
  hasCleanCode: boolean;
  cleanCodeComments: string;
  isRunnable: boolean;
  runnableComments: string;
  reviewerSubmitted: boolean;
  editorUrl: string;
  reviewerName: string;
  reviewStatus:
    | "Awaiting reviewer feedback"
    | "Awaiting editor feedback"
    | "Awaiting author release changes"
    | "Review is complete";
}

export interface ReviewInvitation {
  id: number;
  slug: string;
  candidateReviewer: RelatedMemberProfile;
  reviewer: Reviewer;
  dateCreated: string;
  dateSent: string;
  expirationDate: string;
  optionalMessage: string;
  optionalMessageMarkupType: string;
  accepted: boolean | null;
  review: number;
  editor: number;
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
    metadata: FileInfo[];
  };
  media: FileInfo[];
}

export type FileCategory = keyof CodebaseReleaseFiles["originals"];

export interface FileInfo {
  name: string;
  identifier: string;
}

export interface License {
  name: string;
  url?: string;
}

export interface ReleaseContributor {
  contributor: Contributor;
  includeInCitation?: boolean;
  index?: number;
  profileUrl: string;
  roles?: string[];
}

export interface Contributor {
  affiliations: any[];
  jsonAffiliations: any[];
  primaryAffiliationName: string;
  email: string;
  id: number;
  name: string;
  givenName: string;
  middleName?: string;
  familyName?: string;
  profileUrl?: string;
  type: "person" | "organization";
  user?: RelatedUser | null;
}

export interface RelatedMemberProfile {
  id: number;
  avatarUrl?: string;
  degrees: string[];
  givenName: string;
  middleName?: string;
  familyName: string;
  name: string;
  email: string;
  profileUrl: string;
  primaryAffiliationName?: string;
  tags: Tag[];
  username: string;
}

export interface RelatedUser {
  id: number;
  username: string;
  memberProfile: RelatedMemberProfile;
}

export interface ImportedReleasePackage {
  service: string;
  uid: string;
  name: string;
  displayName: string;
  htmlUrl: string;
}

export interface CodebaseRelease {
  absoluteUrl: string;
  status: "DRAFT" | "UNDER_REVIEW" | "REVIEW_COMPLETE" | "PUBLISHED" | "UNPUBLISHED";
  canEditOriginals: boolean;
  citationText?: string;
  codebase: Codebase;
  dateCreated: Date;
  dependencies?: any;
  documentation: string | null;
  doi: string | null;
  embargoEndDate: Date | null;
  firstPublishedAt: Date | null;
  identifier: string;
  lastModified: Date | null;
  lastPublishedOn: Date | null;
  license: License | null;
  live: boolean;
  os: string;
  osDisplay: string;
  outputDataUrl: string;
  peerReviewed: boolean;
  platforms: Tag[];
  possibleLicenses: License[];
  programmingLanguages: Tag[];
  releaseContributors: ReleaseContributor[];
  releaseNotes: string;
  reviewStatus: string | null;
  shareUrl: string | null;
  submittedPackage: string | null;
  submitter: RelatedUser;
  urls: {
    requestPeerReview: string | null;
    review: string | null;
    notifyReviewersOfChanges: string | null;
  };
  versionNumber: string;
  importedReleaseSyncState?: ImportedReleaseSyncState | null;
}

export interface RelatedCodebase {
  absoluteUrl: string;
  allContributors: Contributor[];
  githubConfigUrl: string;
  activeGitRemote: CodebaseGitRemote | null;
  tags: Tag[];
  title: string;
  firstPublishedAt: Date | null;
  lastPublishedOn: Date | null;
  identifier: string;
  versionNumber?: string;
  featuredImage: string | null;
  summarizedDescription: string;
  description: string;
  live: boolean;
  peerReviewed?: boolean;
  repositoryUrl?: string;
}

interface Codebase {
  absoluteUrl: string;
  allContributors: Contributor[];
  associatedPublicationText?: string;
  dateCreated: Date;
  description: string;
  doi?: string | null;
  downloadCount: number;
  featuredImage: string | null;
  firstPublishedAt: Date | null;
  id: number;
  identifier: string;
  lastPublishedOn: Date | null;
  latestVersionNumber?: string;
  peerReviewed?: boolean;
  referencesText?: string;
  releases?: any[];
  replicationText?: string;
  repositoryUrl?: string;
  submitter: RelatedUser;
  summarizedDescription: string;
  tags: Tag[];
  title: string;
}

export type CodebaseReleaseMetadata = Pick<
  CodebaseRelease,
  | "releaseNotes"
  | "embargoEndDate"
  | "os"
  | "platforms"
  | "programmingLanguages"
  | "live"
  | "license"
>;

export interface UploadSuccess {
  kind: "success";
  msg: string;
}

export interface UploadProgress {
  kind: "progress";
  percentCompleted: number;
  size: number;
}

export interface UploadFailure {
  kind: "failure";
  msgs: { level: string; msg: { detail: string; stage: string } }[];
}

export interface File {
  label: string;
  category: FileCategory;
  pendingCategory?: FileCategory;
  path: string;
}

export interface Folder {
  label: string;
  contents: (File | Folder)[];
}

export interface UserSearchQueryParams {
  query?: string;
  page?: number;
  tags?: string[];
}

export interface ReviewerFilterParams {
  includeInactive?: boolean;
  name?: string;
  programmingLanguages?: string[];
}

export interface FeedItem {
  title: string;
  summary?: string;
  author?: string;
  link: string;
  date?: Date;
  thumbnail?: string;
  doi?: string;
  color?: string;
}

export interface FeedProps {
  feedUrl: string;
  limit: number;
  datePrefix?: string;
  authorPrefix?: string;
}

export interface GithubAccount {
  id: string | number;
  username: string;
  profileUrl: string;
  installationId?: number;
}

export interface GitHubAppInstallationStatus {
  githubAccount: GithubAccount | null;
  connectUrl: string;
  installationUrl: string | null;
}

export type ReleaseSyncStatus = "PENDING" | "RUNNING" | "SUCCESS" | "ERROR";

export interface BaseReleaseSyncState {
  id: number;
  status: ReleaseSyncStatus;
  lastLog: string;
  fullLog: any[];
  errorMessage: string;
  httpStatus: number | null;
  lastSyncStartedAt: string | null;
  lastSyncFinishedAt: string | null;
  batchId?: string | null;
  tagName: string;
  dateCreated: string;
  lastModified: string;
}

export interface PushableReleaseSyncState extends BaseReleaseSyncState {
  remote: number | null;
  release: number;
  builtCommitSha: string;
  lastBuiltAt: string | null;
  pushedCommitSha: string;
  canRepush: boolean;
}

export interface ImportedReleaseSyncState extends BaseReleaseSyncState {
  remote: number | null;
  categoryManifest: Record<string, string>;
  githubReleaseId: string;
  displayName: string;
  htmlUrl: string;
  downloadUrl: string;
  extraData: Record<string, any>;
  canReimport: boolean;
}

export interface CodebaseGitRemote {
  id: number;
  owner: string;
  repoName: string;
  url: string;
  shouldPush: boolean;
  shouldImport: boolean;
  isUserRepo: boolean;
  isPreexisting: boolean;
  isActive: boolean;
  pushableSyncStates: PushableReleaseSyncState[];
  importedSyncStates: ImportedReleaseSyncState[];
}

export interface CodebaseGitRemoteForm {
  shouldPush?: boolean;
  shouldImport?: boolean;
}

export interface CodebaseReleaseWithPushableStates extends CodebaseRelease {
  pushableSyncStates: PushableReleaseSyncState[];
  activeOrNullRemotePushableSyncState?: PushableReleaseSyncState | null;
}

export interface GitHubRelease {
  id: string | number;
  name: string;
  tagName: string;
  htmlUrl: string;
  zipballUrl: string;
  draft: boolean;
  prerelease: boolean;
  createdAt: string | null;
  publishedAt: string | null;
  hasSemanticVersioning: boolean;
  version: string;
  createdByIntegration: boolean;
  importedSyncState?: ImportedReleaseSyncState | null;
}
