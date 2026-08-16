import { FONT, GRAY, INK, LIME, OLIVE, W, GRID } from "./config";

export { GRAY, INK, LIME };

export function font(weight: number, size: number): string {
  return `${weight} ${size}px ${FONT}`;
}

export function rr(
  ctx: CanvasRenderingContext2D,
  x: number,
  y: number,
  w: number,
  h: number,
  r: number,
) {
  ctx.beginPath();
  ctx.moveTo(x + r, y);
  ctx.arcTo(x + w, y, x + w, y + h, r);
  ctx.arcTo(x + w, y + h, x, y + h, r);
  ctx.arcTo(x, y + h, x, y, r);
  ctx.arcTo(x, y, x + w, y, r);
  ctx.closePath();
}

export function wrap(ctx: CanvasRenderingContext2D, text: string, maxW: number): string[] {
  const out: string[] = [];
  let line = "";
  for (const ch of text.replace(/\n/g, " ")) {
    if (ctx.measureText(line + ch).width > maxW && line) {
      out.push(line);
      line = ch;
    } else line += ch;
  }
  if (line) out.push(line);
  return out;
}

export function white(ctx: CanvasRenderingContext2D, x: number, y: number, w: number, h: number) {
  ctx.fillStyle = "#fff";
  ctx.shadowColor = "rgba(23,27,20,0.08)";
  ctx.shadowBlur = 24;
  rr(ctx, x, y, w, h, 40);
  ctx.fill();
  ctx.shadowBlur = 0;
}

export function statBlock(
  ctx: CanvasRenderingContext2D,
  x: number,
  y: number,
  label: string,
  value: string,
  unit = "",
) {
  ctx.fillStyle = GRAY;
  ctx.font = font(500, 30);
  ctx.fillText(label, x, y);
  ctx.fillStyle = INK;
  ctx.font = font(800, 76);
  ctx.fillText(value, x, y + 90);
  if (unit) {
    const vw = ctx.measureText(value).width;
    ctx.font = font(500, 30);
    ctx.fillStyle = GRAY;
    ctx.fillText(unit, x + vw + 12, y + 90);
  }
}

export function header(ctx: CanvasRenderingContext2D, title: string, sub: string) {
  const config = {
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
    headerHeight: 420,
  };

  ctx.fillStyle = OLIVE;
  ctx.fillRect(0, 0, W, config.headerHeight);

  ctx.fillStyle = LIME;
  ctx.beginPath();
  ctx.arc(config.ballCenterX, config.ballCenterY, config.ballRadius, 0, Math.PI * 2);
  ctx.fill();

  ctx.strokeStyle = "rgba(255,255,255,0.55)";
  ctx.lineWidth = 7;
  ctx.beginPath();
  ctx.arc(W - 260, config.ballCenterY, config.arcRadius, config.arcStartAngle, config.arcEndAngle);
  ctx.stroke();

  ctx.fillStyle = LIME;
  ctx.font = font(600, config.brandFontSize);
  ctx.fillText("TENNIS DIARY 🎾", 70, config.brandY);

  ctx.fillStyle = "#fff";
  ctx.font = font(700, config.titleFontSize);
  ctx.fillText(title, 70, config.titleY);

  ctx.fillStyle = "rgba(255,255,255,0.65)";
  ctx.font = font(400, config.subtitleFontSize);
  ctx.fillText(sub, 70, config.subtitleY);
}

export function footer(ctx: CanvasRenderingContext2D, h: number) {
  ctx.fillStyle = GRAY;
  ctx.font = font(500, 30);
  ctx.fillText("用 Tennis Diary 记录我的网球成长 🎾", 70, h - 80);
}

export function emptyCard(ctx: CanvasRenderingContext2D, text: string) {
  const config = {
    x: 70,
    y: 480,
    w: 940,
    h: 700,
    textY: 830,
  };

  ctx.fillStyle = "#fff";
  rr(ctx, config.x, config.y, config.w, config.h, 40);
  ctx.fill();

  ctx.fillStyle = INK;
  ctx.font = font(700, 44);
  ctx.fillText(text, config.x, config.textY);
}

export function drawRadar(
  ctx: CanvasRenderingContext2D,
  cx: number,
  cy: number,
  R: number,
  data: { name: string; score: number }[],
) {
  const n = data.length;
  if (n < 3) return;

  const angle = (i: number) => -Math.PI / 2 + (2 * Math.PI * i) / n;
  const pt = (i: number, r: number) => ({
    x: cx + r * Math.cos(angle(i)),
    y: cy + r * Math.sin(angle(i)),
  });

  ctx.lineWidth = 1;
  for (const ratio of [0.33, 0.66, 1]) {
    ctx.beginPath();
    for (let i = 0; i < n; i++) {
      const p = pt(i, R * ratio);
      if (i === 0) ctx.moveTo(p.x, p.y);
      else ctx.lineTo(p.x, p.y);
    }
    ctx.closePath();
    ctx.strokeStyle = GRID;
    ctx.stroke();
  }

  for (let i = 0; i < n; i++) {
    const p = pt(i, R);
    ctx.beginPath();
    ctx.moveTo(cx, cy);
    ctx.lineTo(p.x, p.y);
    ctx.strokeStyle = GRID;
    ctx.stroke();
  }

  ctx.beginPath();
  for (let i = 0; i < n; i++) {
    const v = Math.min(Number(data[i].score) || 0, 100) / 100;
    const p = pt(i, R * v);
    if (i === 0) ctx.moveTo(p.x, p.y);
    else ctx.lineTo(p.x, p.y);
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

  ctx.textAlign = "center";
  ctx.textBaseline = "middle";
  for (let i = 0; i < n; i++) {
    const lp = pt(i, R + 18);
    ctx.font = font(500, 26);
    ctx.fillStyle = GRAY;
    ctx.fillText(String(data[i].name), lp.x, lp.y - 8);
    ctx.font = font(700, 28);
    ctx.fillStyle = INK;
    ctx.fillText(String(Math.round(Number(data[i].score) || 0)), lp.x, lp.y + 10);
  }
}

export function fmtDuration(min: number): string {
  if (min < 60) return `${min}分钟`;
  const h = Math.floor(min / 60);
  const m = min % 60;
  return m ? `${h}小时${m}分` : `${h}小时`;
}

export function fmtMoney(n: number): string {
  return n % 1 === 0 ? `¥${n}` : `¥${n.toFixed(2)}`;
}

export function sumCosts(costs: { amount: number }[]): number {
  return costs.reduce((s, c) => s + (Number(c.amount) || 0), 0);
}
