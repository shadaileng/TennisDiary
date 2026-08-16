import { createCanvas } from "@napi-rs/canvas";

export interface RadarData {
  name: string;
  score: number;
}

export interface LineData {
  label: string;
  value: number;
}

const GRID = "#E7E9DF";
const LIME = "#C8DA2B";
const INK = "#171B14";
const GREY = "#9CA3AF";

/**
 * Render RadarChart to buffer using @napi-rs/canvas
 */
export function renderRadarChart(
  data: RadarData[],
  width: number = 320,
  height: number = 220,
): Buffer {
  const canvas = createCanvas(width, height);
  const ctx = canvas.getContext("2d");

  // Background
  ctx.fillStyle = "#ffffff";
  ctx.fillRect(0, 0, width, height);

  if (data.length < 3) {
    // Placeholder text
    ctx.fillStyle = GREY;
    ctx.font = "12px sans-serif";
    ctx.textAlign = "center";
    ctx.textBaseline = "middle";
    ctx.fillText("暂无评分数据", width / 2, height / 2);
    return canvas.toBuffer("image/png");
  }

  const cx = width / 2;
  const cy = height / 2;
  const R = Math.min(width / 2, height / 2) - 42;
  if (R < 20) {
    return canvas.toBuffer("image/png");
  }

  const n = data.length;
  const angle = (i: number) => -Math.PI / 2 + (2 * Math.PI * i) / n;
  const pt = (i: number, r: number) => ({
    x: cx + r * Math.cos(angle(i)),
    y: cy + r * Math.sin(angle(i)),
  });

  // Grid rings (0.33 / 0.66 / 1)
  ctx.lineWidth = 1;
  for (const ratio of [0.33, 0.66, 1]) {
    ctx.beginPath();
    for (let i = 0; i < n; i++) {
      const p = pt(i, R * ratio);
      if (i === 0) {
        ctx.moveTo(p.x, p.y);
      } else {
        ctx.lineTo(p.x, p.y);
      }
    }
    ctx.closePath();
    ctx.strokeStyle = GRID;
    ctx.stroke();
  }

  // Radial lines
  for (let i = 0; i < n; i++) {
    const p = pt(i, R);
    ctx.beginPath();
    ctx.moveTo(cx, cy);
    ctx.lineTo(p.x, p.y);
    ctx.strokeStyle = GRID;
    ctx.stroke();
  }

  // Score polygon
  ctx.beginPath();
  for (let i = 0; i < n; i++) {
    const v = Math.min(Number(data[i].score) || 0, 100) / 100;
    const p = pt(i, R * v);
    if (i === 0) {
      ctx.moveTo(p.x, p.y);
    } else {
      ctx.lineTo(p.x, p.y);
    }
  }
  ctx.closePath();
  ctx.fillStyle = LIME;
  ctx.globalAlpha = 0.35;
  ctx.fill();
  ctx.globalAlpha = 1;
  ctx.strokeStyle = LIME;
  ctx.lineWidth = 2;
  ctx.lineJoin = "round";
  ctx.stroke();

  // Vertex labels
  ctx.textAlign = "center";
  ctx.textBaseline = "middle";
  for (let i = 0; i < n; i++) {
    const lp = pt(i, R + 18);
    ctx.font = "bold 11px sans-serif";
    ctx.fillStyle = GREY;
    ctx.fillText(String(data[i].name), lp.x, lp.y - 8);
    ctx.fillStyle = INK;
    ctx.fillText(
      String(Math.round(Number(data[i].score) || 0)),
      lp.x,
      lp.y + 7,
    );
  }

  return canvas.toBuffer("image/png");
}

/**
 * Render LineChart to buffer using @napi-rs/canvas
 */
export function renderLineChart(
  data: LineData[],
  width: number = 320,
  height: number = 120,
  color: string = LIME,
  unit: string = "",
): Buffer {
  const canvas = createCanvas(width, height);
  const ctx = canvas.getContext("2d");

  // Background
  ctx.fillStyle = "#ffffff";
  ctx.fillRect(0, 0, width, height);

  if (data.length === 0) {
    ctx.fillStyle = GREY;
    ctx.font = "12px sans-serif";
    ctx.textAlign = "center";
    ctx.textBaseline = "middle";
    ctx.fillText("暂无数据", width / 2, height / 2);
    return canvas.toBuffer("image/png");
  }

  const vals = data.map((d) => d.value);
  const min = Math.min(...vals);
  const max = Math.max(...vals);
  const range = max - min || 1;
  const padX = 10;
  const padY = 18;
  const stepX = data.length > 1 ? (width - padX * 2) / (data.length - 1) : 0;

  const pts = data.map((d, i) => ({
    x: padX + i * stepX,
    y: padY + (height - padY * 2) * (1 - (d.value - min) / range),
  }));

  // Area fill
  ctx.beginPath();
  ctx.moveTo(pts[0].x, pts[0].y);
  for (let i = 1; i < pts.length; i++) ctx.lineTo(pts[i].x, pts[i].y);
  ctx.lineTo(pts[pts.length - 1].x, height - 6);
  ctx.lineTo(pts[0].x, height - 6);
  ctx.closePath();
  ctx.fillStyle = color;
  ctx.globalAlpha = 0.15;
  ctx.fill();
  ctx.globalAlpha = 1;

  // Line
  ctx.beginPath();
  ctx.moveTo(pts[0].x, pts[0].y);
  for (let i = 1; i < pts.length; i++) ctx.lineTo(pts[i].x, pts[i].y);
  ctx.strokeStyle = color;
  ctx.lineWidth = 2.5;
  ctx.lineCap = "round";
  ctx.lineJoin = "round";
  ctx.stroke();

  // Data points + labels
  ctx.font = "10px sans-serif";
  ctx.textAlign = "center";
  for (let i = 0; i < pts.length; i++) {
    const p = pts[i];
    ctx.beginPath();
    ctx.arc(p.x, p.y, 3, 0, Math.PI * 2);
    ctx.fillStyle = "#ffffff";
    ctx.fill();
    ctx.strokeStyle = color;
    ctx.lineWidth = 2;
    ctx.stroke();

    const isEdge =
      i === 0 ||
      i === pts.length - 1 ||
      data[i].value === max ||
      data[i].value === min;
    if (isEdge) {
      const n = Number(data[i].value);
      const label = Number.isInteger(n)
        ? String(n)
        : n.toFixed(1);
      ctx.fillStyle = INK;
      ctx.font = "10px sans-serif";
      ctx.fillText(`${label}${unit}`, p.x, p.y - 8);
    }
  }

  // X-axis labels
  ctx.fillStyle = GREY;
  ctx.font = "9px sans-serif";
  if (data.length <= 8) {
    data.forEach((d, i) => {
      ctx.fillText(d.label, pts[i].x, height - 2);
    });
  } else {
    ctx.textAlign = "start";
    ctx.fillText(data[0].label, pts[0].x, height - 2);
    ctx.textAlign = "end";
    ctx.fillText(
      data[data.length - 1].label,
      pts[pts.length - 1].x,
      height - 2,
    );
  }

  return canvas.toBuffer("image/png");
}
