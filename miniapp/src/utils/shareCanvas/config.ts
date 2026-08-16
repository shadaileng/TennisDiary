import type { Analysis, Diary } from "@/types";

export const W = 1080;
export const LIME = "#C8DA2B";
export const OLIVE = "#242B1F";
export const PAPER = "#F2F2EF";
export const INK = "#171B14";
export const GRAY = "#9AA096";
export const GRID = "#E7E9DF";
export const FONT = "Microsoft YaHei, PingFang SC, sans-serif";

export type ShareTemplate = "月度战报" | "今日日记" | "技术评分";
export const SHARE_TEMPLATES: readonly ShareTemplate[] = ["月度战报", "今日日记", "技术评分"] as const;

export interface ShareData {
  diaries: Diary[];
  analysis?: Analysis;
}

export interface MoodItem {
  v: number;
  label: string;
  emoji: string;
}

export interface IntensityItem {
  v: number;
  label: string;
  emoji: string;
}

export const PIPELINE_CONFIG = {
  canvas: { width: W },
  headerHeight: 420,
  footer: { height: 100, padding: 80, bottomMargin: 100 },
  content: { top: 460 as number, padding: 70, cardWidth: 940 },
  card: { radius: 40 },
  monthlyStats: {
    cardWidth: 450,
    cardHeight: 320,
    leftX: 70,
    rightX: 560,
    topY: 480,
    gap: 360,
    labelY: 570,
    valueY: 680,
    emojiY: 780,
  },
  todayDiary: {
    cardTop: 480,
    intensityCard: { x: 70, y: 480, w: 450, h: 280 },
    moodCard: { x: 560, y: 480, w: 450, h: 280 },
    reviewCard: { x: 70, y: 800, w: 940, h: 400 },
    labelY: 565,
    emojiY: 680,
    labelValueY: 665,
    reviewTitleY: 875,
    reviewTextStartY: 945,
    reviewMaxY: 1140,
    reviewTextWidth: 820,
    lineHeight: 58,
  },
  techScore: {
    cardTop: 480,
    radar: { cx: W / 2, cy: 710, radius: 110 },
    radarZone: { top: 480, height: 460 },
    progressZone: { top: 980, itemHeight: 175 },
    summaryZone: { height: 180, lineHeight: 45 },
    dimNameX: 120,
    dimScoreX: 940,
    barX: 120,
    barWidth: 780,
    barHeight: 18,
    barRadius: 9,
    barTopOffset: 35,
    commentStartOffset: 80,
    commentMaxLines: 2,
    commentLineHeight: 40,
    commentFontSize: 26,
    scoreBall: { cy: 720, radius: 130, fontSize: 110 },
    scoreBallCard: { x: 70, y: 470, w: 940, h: 600 },
  },
  emptyCard: { x: 70, y: 480, w: 940, h: 700, textY: 830 },
  header: {
    brandY: 120,
    titleY: 230,
    subtitleY: 300,
    brandFontSize: 34,
    titleFontSize: 84,
    subtitleFontSize: 34,
    ballCenterX: W - 130,
    ballCenterY: 130,
    ballRadius: 150,
    arcRadius: 190,
    arcStartAngle: -0.5,
    arcEndAngle: 0.7,
  },
} as const;
