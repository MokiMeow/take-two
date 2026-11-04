import { Composition, Still, staticFile } from "remotion";
import { loadFont } from "@remotion/fonts";
import { Preview } from "./Preview";
import { CallSheet } from "./CallSheet";
import { callSheetDefaults, callSheetSchema, previewDefaults, previewSchema } from "./schema";

const FONTS: [string, string, string?][] = [
  ["Courier Prime", "courier-prime-latin-400-normal.woff2", "400"],
  ["Courier Prime", "courier-prime-latin-700-normal.woff2", "700"],
  ["Instrument Serif", "instrument-serif-latin-400-normal.woff2", "400"],
  ["Geist", "geist-latin-wght-normal.woff2", "100 900"],
  ["Geist Mono", "geist-mono-latin-wght-normal.woff2", "100 900"],
];
for (const [family, file, weight] of FONTS) {
  loadFont({ family, url: staticFile(`fonts/${file}`), weight, format: "woff2" });
}

export const Root: React.FC = () => (
  <>
    <Composition
      id="Preview"
      component={Preview}
      durationInFrames={75}
      fps={15}
      width={960}
      height={540}
      schema={previewSchema}
      defaultProps={previewDefaults}
    />
    <Still id="CallSheet" component={CallSheet} width={1200} height={1360} schema={callSheetSchema} defaultProps={callSheetDefaults} />
  </>
);
