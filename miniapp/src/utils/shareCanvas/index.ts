export { DrawPipeline } from "./pipeline";
export type { DrawStage, DrawStep } from "./pipeline";
export { buildContext } from "./context";
export type { PipelineContext } from "./context";
export { PIPELINE_CONFIG, SHARE_TEMPLATES } from "./config";
export type { ShareTemplate, ShareData, MoodItem, IntensityItem } from "./config";
export { headerStage } from "./stages/header";
export { footerStage } from "./stages/footer";
export { monthlyStage } from "./stages/monthly";
export { todayDiaryStage } from "./stages/todayDiary";
export { radarStage, progressStage, summaryStage } from "./stages/techScore";
export { genCaption } from "./caption";

import { DrawPipeline } from "./pipeline";
import { headerStage } from "./stages/header";
import { footerStage } from "./stages/footer";
import { monthlyStage } from "./stages/monthly";
import { todayDiaryStage } from "./stages/todayDiary";
import { radarStage, progressStage, summaryStage } from "./stages/techScore";
import { buildContext } from "./context";
import type { ShareTemplate, ShareData, MoodItem, IntensityItem } from "./config";

export function createPipeline(): DrawPipeline {
  return new DrawPipeline()
    .addStage(headerStage)
    .addStage(monthlyStage)
    .addStage(todayDiaryStage)
    .addStage(radarStage)
    .addStage(progressStage)
    .addStage(summaryStage)
    .addStage(footerStage);
}

export function drawShareCard(
  ctx: CanvasRenderingContext2D,
  tpl: ShareTemplate,
  data: ShareData,
  MOOD: readonly MoodItem[],
  INTENSITY: readonly IntensityItem[],
  qrImage?: CanvasImageSource,
): number {
  const pipe = buildContext(tpl, data, MOOD, INTENSITY, qrImage);
  const pipeline = createPipeline();
  return pipeline.execute(ctx, pipe);
}

export function measureShareCardHeight(
  tpl: ShareTemplate,
  data: ShareData,
  MOOD: readonly MoodItem[],
  INTENSITY: readonly IntensityItem[],
  qrImage?: CanvasImageSource,
): number {
  const pipe = buildContext(tpl, data, MOOD, INTENSITY, qrImage);
  const pipeline = createPipeline();
  return pipeline.measureHeight(pipe);
}
