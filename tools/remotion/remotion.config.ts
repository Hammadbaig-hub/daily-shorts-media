/**
 * Remotion config for the Bright Life "Myth ya Fact?" renderer.
 * Rendering is normally driven by tools/scripts/make_remotion_short.py.
 */
import fs from "node:fs";
import { Config } from "@remotion/cli/config";

Config.setRspack(true);
Config.setVideoImageFormat("jpeg");
Config.setOverwriteOutput(true);
Config.setDefaultPremountInSeconds(2);

// The cloud sandbox can't download Remotion's Chrome; use the preinstalled one.
const chrome =
  process.env.REMOTION_CHROME ||
  "/opt/pw-browsers/chromium_headless_shell-1243/chrome-headless-shell-linux64/chrome-headless-shell";
if (fs.existsSync(chrome)) {
  Config.setBrowserExecutable(chrome);
}
