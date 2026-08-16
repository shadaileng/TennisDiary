import type { Analysis, Diary } from "@/types";
import { PIPELINE_CONFIG } from "./config";
import type { MoodItem, IntensityItem, ShareData, ShareTemplate } from "./config";

export interface PipelineContext {
  tpl: ShareTemplate;
  data: ShareData;
  config: typeof PIPELINE_CONFIG;
  MOOD: readonly MoodItem[];
  INTENSITY: readonly IntensityItem[];
  monthDiaries: Diary[];
  latestDiary?: Diary;
  latestAnalysis?: Analysis;
  monthKey: string;
}

function monthKeyFromDate(dateStr: string): string {
  return dateStr.slice(0, 7);
}

function todayStr(): string {
  const d = new Date();
  const pad = (n: number) => (n < 10 ? `0${n}` : `${n}`);
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;
}

export function buildContext(
  tpl: ShareTemplate,
  data: ShareData,
  MOOD: readonly MoodItem[],
  INTENSITY: readonly IntensityItem[],
): PipelineContext {
  const currentMonthKey = monthKeyFromDate(todayStr());
  const monthDiaries = data.diaries.filter((d) => monthKeyFromDate(d.date) === currentMonthKey);
  const latestDiary = data.diaries[0];
  const latestAnalysis = data.analysis;

  return {
    tpl,
    data,
    config: PIPELINE_CONFIG,
    MOOD,
    INTENSITY,
    monthDiaries,
    latestDiary,
    latestAnalysis,
    monthKey: currentMonthKey,
  };
}
