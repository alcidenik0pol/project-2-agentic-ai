import type { DataSource } from "@/lib/types";
import { DATASET_CARDS } from "@/lib/datasets";

// Data source options for the dropdown.
//
// Single source of truth: frontend/lib/datasets.ts. To add a dataset or change
// its label/description, edit the corresponding DATASET_CARDS entry — do NOT
// duplicate facts here.
export const DATA_SOURCES: { value: DataSource; label: string; description: string }[] =
  (Object.keys(DATASET_CARDS) as DataSource[]).map((id) => ({
    value: id,
    label: DATASET_CARDS[id].dropdownLabel,
    description: DATASET_CARDS[id].description,
  }));
