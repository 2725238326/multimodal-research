// Registry entity types — mirror platform/labkit/schema.py.

export interface Metric {
  value: number;
  ci95: [number, number] | null;
  unit: string;
}

export interface Idea {
  id: string;
  title: string;
  slot: "mainline" | "adjacent" | "high_risk" | "pool";
  status: "proposed" | "active" | "blocked" | "parked" | "done";
  thesis: string;
  detail: string;
  design_patterns: string[];
  collision_notes: string;
  experiment_ids: string[];
  links: string[];
}

export interface Condition {
  name: string;
  purpose: string;
  changed_var: string;
}

export interface ControlSet {
  correct: string;
  wrong: string;
  shuffled: string;
  irrelevant: string;
  equal_param: string;
}

export interface Experiment {
  id: string;
  title: string;
  idea_id: string;
  question: string;
  hypothesis: string;
  track: "exploratory" | "confirmatory";
  status: string;
  conditions: Condition[];
  controls: ControlSet;
  primary_metric: string;
  guardrail_metrics: string[];
  go_threshold: string;
  no_go_threshold: string;
  statistical_unit: string;
  bootstrap_unit: string;
  plan_md_path: string;
  config_path: string;
  run_ids: string[];
}

export interface Artifact {
  name: string;
  path: string;
  tracked: boolean;
}

export interface ChartSpec {
  id: string;
  title: string;
  subtitle: string;
  type: string;
  dataset: string;
  valueFormat?: string;
  encodings: Record<string, { field: string; type?: string; format?: string }>;
}

export interface Run {
  id: string;
  experiment_id: string;
  title: string;
  commit: string;
  seed: number | null;
  device: string;
  command: string;
  metrics: Record<string, Metric>;
  conditions_metrics: any[];
  charts: ChartSpec[];
  datasets: Record<string, any[]>;
  verdict: "go" | "no_go" | "uncertain" | "pending";
  verdict_reason: string;
  artifacts: Artifact[];
  notes: string;
}

export interface Dataset {
  id: string;
  name: string;
  version: string;
  manifest_hash: string;
  license_status: string;
  path: string;
  independent_units: { scenes: number; regions: number; samples: number };
  notes: string;
}

export interface Module {
  id: string;
  name: string;
  kind_: string;
  path: string;
  notes: string;
}

export interface Registry {
  ideas: Idea[];
  experiments: Experiment[];
  runs: Run[];
  datasets: Dataset[];
  modules: Module[];
}

export interface RegistryResponse {
  data: Registry;
  problems: string[];
}

export async function fetchRegistry(): Promise<RegistryResponse> {
  const res = await fetch("/api/registry");
  if (!res.ok) throw new Error(`registry fetch failed: ${res.status}`);
  return res.json();
}
