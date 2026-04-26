export type Recency = "current_window" | "recent_context" | "historical_context" | "unknown";

export interface MatchInfo {
  athlete_a: string;
  athlete_b: string;
  arm: string;
  event_context: string;
  product_positioning: string;
}

export interface Summary {
  claim_count: number;
  source_count: number;
  current_form_claim_count: number;
  recency_distribution: Partial<Record<Recency, number>>;
  dimension_count: number;
  mechanics_dimension_count: number;
  measurement_dimension_count: number;
  lift_dimension_count: number;
  mechanism_atom_count: number;
  theme_count: number;
}

export interface Source {
  video_id: string;
  title: string;
  channel: string;
  claim_count: number;
  source_recency: Recency;
  url: string;
}

export interface ThemeEvidenceRef {
  evidence_index: number;
  role_in_theme?: string;
}

export interface Theme {
  theme_id: string;
  label: string;
  why_this_theme_emerged: string;
  match_relevance: string;
  evidence_refs: ThemeEvidenceRef[];
  challenged_assumption?: string;
  current_form_read?: string;
  historical_style_read?: string;
  confidence?: string;
}

export interface SourceGap {
  gap: string;
  why_it_matters: string;
  suggested_source_query: string;
}

export type DimensionValue = string | Record<string, string | number | boolean | null | undefined>;

export interface EvidenceDimension {
  evidence_index: number;
  evidence_kind: string;
  temporal_scope: string;
  subject_athletes: string[];
  arm_side: string;
  mechanics: string[];
  table_positions: string[];
  physical_attributes: string[];
  measurements: DimensionValue[];
  lifts: DimensionValue[];
  transferable_lessons: string[];
  current_form_usable: boolean;
  durable_style_usable: boolean;
  historical_context_usable: boolean;
  verification_needed: string[];
  noise_risk: string;
  dimension_confidence: string;
  abstained_dimensions: string[];
}

export interface MechanismAtom {
  evidence_index: number;
  subject: string;
  mechanism: string;
  lane: string;
  polarity: string;
  claim_role: string;
  confidence: string;
}

export interface Claim {
  evidence_index: number;
  claim: string;
  timestamp: string;
  source_url: string;
  speaker_or_source: string;
  relevance: string;
  confidence: string;
  source_published_at: string;
  source_age_days: number;
  source_recency: Recency;
  current_form_allowed: boolean;
  allowed_evidence_roles: string[];
  video_id: string;
  video_title: string;
  channel: string;
  selected_model: string;
  dimensions?: EvidenceDimension;
  mechanism_atoms: MechanismAtom[];
}

export interface Dossier {
  generated_at: string;
  match: MatchInfo;
  summary: Summary;
  sources: Source[];
  themes: Theme[];
  cross_theme_tensions: string[];
  source_gaps: SourceGap[];
  mechanism_conflicts: unknown[];
  claims: Claim[];
}
