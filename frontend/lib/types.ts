export interface BoundingBox {
  x: number;
  y: number;
  width: number;
  height: number;
}

export interface HighlightedElement {
  rule_id_ref: string | null;
  bounding_box: BoundingBox;
  status: "correct" | "wrong" | "info";
  message: string;
  found_value: string | null;
  expected_value: string | null;
  confidence: number | null;
}

export interface LabelAnalysisResult {
  analysis_id: string; // UUID is a string in TypeScript
  original_filename: string;
  overall_status: "pass" | "fail_critical" | "fail_minor" | "processing_error";
  summary: Record<string, any>; // A flexible object for summary stats
  highlights: HighlightedElement[];
  timestamp: string; // ISO date string
}

// Minimal type for the rule structure for now
export interface RuleCondition {
  type: string;
  target_element_description?: string;
  expected_text?: string;
  // Add other rule properties as needed
}

export interface RuleSet {
  name: string;
  description?: string;
  conditions: RuleCondition[];
}

// For the 202 Accepted response when a task is submitted
export interface AnalysisSubmissionResponse {
  message: string;
  analysis_id: string; // UUID
}
