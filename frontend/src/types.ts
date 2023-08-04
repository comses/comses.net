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
  emailAddress?: string;
  ipAddresses?: any[];
  established?: number | null;
  types: string[];
  relationships: any[];
  addresses: any[];
  links: string[];
  aliases: string[];
  acronyms: string[];
  status: "Active" | "Inactive" | "Withdrawn";
  wikipediaUrl?: string;
  labels: string[];
  country: object;
  externalIds: any;
  [key: string | number | symbol]: unknown;
}

export interface Organization {
  name: string;
  url?: string;
  acronym?: string;
  rorId?: string;
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
  name: string;
  avatarUrl: string;
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
  email: string;
  id: number;
  givenName: string;
  middleName?: string;
  familyName?: string;
  profileUrl?: string;
  type: "person" | "organization";
  user?: {
    institutionName?: string;
    institutionUrl?: string;
    name: string;
    profileUrl: string;
    username: string;
    email: string;
  } | null;
}

export interface LinkedUser {
  name: string;
  profileUrl: string;
  username: string;
}

export interface CodebaseRelease {
  absoluteUrl: string;
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
  submitter: LinkedUser;
  urls: {
    requestPeerReview: string | null;
    review: string | null;
    notifyReviewersOfChanges: string | null;
  };
  versionNumber: string;
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
  submitter: LinkedUser;
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
}

export interface Folder {
  label: string;
  contents: (File | Folder)[];
}
