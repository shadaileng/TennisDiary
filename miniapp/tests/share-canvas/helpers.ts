import { createCanvas } from "@napi-rs/canvas";
import { DrawPipeline } from "../../src/utils/shareCanvas/pipeline";
import { buildContext } from "../../src/utils/shareCanvas/context";
import { headerStage } from "../../src/utils/shareCanvas/stages/header";
import { footerStage } from "../../src/utils/shareCanvas/stages/footer";
import { monthlyStage } from "../../src/utils/shareCanvas/stages/monthly";
import { todayDiaryStage } from "../../src/utils/shareCanvas/stages/todayDiary";
import { techScoreStage } from "../../src/utils/shareCanvas/stages/techScore";
import type { ShareTemplate, ShareData, MoodItem, IntensityItem } from "../../src/utils/shareCanvas/config";

const W = 1080;

const DEFAULT_MOOD: readonly MoodItem[] = [
  { v: 1, label: "沮丧", emoji: "😞" },
  { v: 2, label: "一般", emoji: "😐" },
  { v: 3, label: "开心", emoji: "😄" },
  { v: 4, label: "兴奋", emoji: "🤩" },
  { v: 5, label: "狂喜", emoji: "🥳" },
] as const;

const DEFAULT_INTENSITY: readonly IntensityItem[] = [
  { v: 1, label: "轻松", emoji: "🟢" },
  { v: 2, label: "适中", emoji: "🟡" },
  { v: 3, label: "高强度", emoji: "🔴" },
] as const;

function createTestPipeline(): DrawPipeline {
  return new DrawPipeline()
    .addStage(headerStage)
    .addStage(monthlyStage)
    .addStage(todayDiaryStage)
    .addStage(techScoreStage)
    .addStage(footerStage);
}

export async function renderShareCard(
  tpl: ShareTemplate,
  data: ShareData,
): Promise<{ image: Buffer; height: number }> {
  const pipe = buildContext(tpl, data, DEFAULT_MOOD, DEFAULT_INTENSITY);
  const pipeline = createTestPipeline();
  const height = pipeline.measureHeight(pipe);

  const canvas = createCanvas(W, height);
  const ctx = canvas.getContext("2d");
  pipeline.execute(ctx, pipe);

  return {
    image: canvas.toBuffer("image/png"),
    height,
  };
}

export function createMonthlyData(count: number): ShareData {
  const today = new Date();
  const year = today.getFullYear();
  const month = today.getMonth() + 1;
  const pad = (n: number) => (n < 10 ? `0${n}` : `${n}`);

  const diaries = Array.from({ length: count }, (_, i) => ({
    id: i + 1,
    date: `${year}-${pad(month)}-${pad(Math.min(i + 1, 28))}`,
    time: "10:00",
    type: "网球训练",
    duration: 60 + Math.floor(Math.random() * 60),
    mood: 3 + Math.floor(Math.random() * 3),
    intensity: 1 + Math.floor(Math.random() * 3),
    notes: `第${i + 1}次训练笔记`,
    costs: [{ amount: 50 + Math.floor(Math.random() * 100) }],
  }));

  return { diaries };
}

export function createTodayDiaryData(notes?: string): ShareData {
  const today = new Date();
  const pad = (n: number) => (n < 10 ? `0${n}` : `${n}`);
  const dateStr = `${today.getFullYear()}-${pad(today.getMonth() + 1)}-${pad(today.getDate())}`;

  return {
    diaries: [
      {
        id: 1,
        date: dateStr,
        time: "14:30",
        type: "网球训练",
        duration: 90,
        mood: 4,
        intensity: 2,
        notes: notes || "今天练习了正手击球，感觉进步明显。",
        costs: [],
      },
    ],
  };
}

export function createTechScoreData(dimCount: number): ShareData {
  const names = ["正手", "反手", "发球", "截步", "移动", "战术"];
  const dimensions = Array.from({ length: dimCount }, (_, i) => ({
    name: names[i] || `维度${i + 1}`,
    score: 60 + Math.floor(Math.random() * 40),
    comment: (names[i] || `维度${i + 1}`) + "点评内容",
  }));

  return {
    diaries: [],
    analysis: {
      id: 1,
      kind: "技术",
      date: "2026-08-16",
      score: 78,
      summary: "整体表现不错，各维度均衡发展。",
      report: {
        dimensions,
        improvements: [{ issue: "需要加强反手稳定性" }],
      },
    } as any,
  };
}

export function createEmptyData(): ShareData {
  return { diaries: [] };
}
