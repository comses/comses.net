export interface BaseFieldProps {
  name: string;
  label?: string;
  help?: string;
  placeholder?: string;
  required?: boolean;
}

export type Tags = { name: string }[];
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
  [x: string | number | symbol]: unknown;
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
