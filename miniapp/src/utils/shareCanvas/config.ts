import type { Analysis, Diary } from "@/types";

export const W = 1080;
export const LIME = "#C8DA2B";
export const OLIVE = "#242B1F";
export const PAPER = "#F2F2EF";
export const INK = "#171B14";
export const GRAY = "#9AA096";
export const GRID = "#E7E9DF";
export const FONT = "sans-serif";

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
    cardHeight: 300,
    leftX: 70,
    rightX: 560,
    topY: 480,
    gap: 340,
    labelY: 570,
    valueY: 660,
    emojiY: 760,
  },
  todayDiary: {
    cardTop: 480,
    intensityCard: { x: 70, y: 480, w: 450, h: 280 },
    moodCard: { x: 560, y: 480, w: 450, h: 280 },
    reviewCard: { x: 70, y: 800, w: 940, h: 380 },
    labelY: 570,
    emojiY: 680,
    labelValueY: 665,
    reviewTitleY: 880,
    reviewTextStartY: 950,
    reviewMaxY: 1120,
    reviewTextWidth: 820,
    lineHeight: 58,
  },
  techScore: {
    cardTop: 470,
    radar: { cx: W / 2, cy: 600, radius: 90 },
    dimListTop: 740,
    dimItemHeight: 100,
    dimNameX: 120,
    dimScoreX: 940,
    barX: 120,
    barWidth: 800,
    barHeight: 10,
    barRadius: 5,
    commentStartOffset: 40,
    commentMaxLines: 2,
    commentLineHeight: 30,
    commentFontSize: 24,
    summaryLineHeight: 36,
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
