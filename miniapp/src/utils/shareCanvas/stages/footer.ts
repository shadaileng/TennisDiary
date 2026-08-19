import { footer as drawFooter, font, GRAY, LIME } from "../primitives";
import { W } from "../config";
import type { DrawStage } from "../pipeline";

export const footerStage: DrawStage = {
  name: "footer",
  steps: [
    {
      name: "footer",
      condition: () => true,
      // measure 不需要，因为 pipeline.measureHeight 会自动添加 footer.height
      execute: (ctx, pipe, y) => {
        const H = y + pipe.config.footer.height;

        if (pipe.qrImage) {
          const { qr, height } = pipe.config.footer;
          const qrY = y + (height - qr.size) / 2;
          const qrX = W - qr.marginRight - qr.size;
          const labelRight = qrX - 40;
          const centerY = qrY + qr.size / 2;

          ctx.drawImage(
            pipe.qrImage as CanvasImageSource,
            qrX,
            qrY,
            qr.size,
            qr.size,
          );

          ctx.textAlign = "right";
          ctx.fillStyle = LIME;
          ctx.font = font(700, qr.labelFontSize);
          ctx.fillText(qr.label, labelRight, centerY - 6);

          ctx.fillStyle = GRAY;
          ctx.font = font(500, qr.subLabelFontSize);
          ctx.fillText(qr.subLabel, labelRight, centerY + 26);
          ctx.textAlign = "left";
        }

        drawFooter(ctx, H);
        return y;
      },
    },
  ],
};