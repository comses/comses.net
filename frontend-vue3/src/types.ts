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
