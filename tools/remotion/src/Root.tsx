import React from "react";
import { CalculateMetadataFunction, Composition, continueRender, delayRender, staticFile } from "remotion";
import { MythShort, W, H } from "./MythShort";
import { Timeline } from "./types";
import sample from "./sample-timeline.json";

type Props = { timeline: Timeline; audio: string };

// Load the Urdu (Nastaliq) and English fonts before any frame is captured
const fontHandle = delayRender("Loading fonts");
Promise.all([
  new FontFace("NotoNastaliq", `url(${staticFile("fonts/NotoNastaliqUrdu-VF.ttf")})`, { weight: "400 700" }).load(),
  new FontFace("Montserrat", `url(${staticFile("fonts/Montserrat-VF.ttf")})`, { weight: "100 900" }).load(),
])
  .then((fonts) => {
    fonts.forEach((f) => document.fonts.add(f));
    continueRender(fontHandle);
  })
  .catch((err) => {
    console.error(err);
    continueRender(fontHandle);
  });

const calculateMetadata: CalculateMetadataFunction<Props> = ({ props }) => ({
  durationInFrames: Math.ceil(props.timeline.total * props.timeline.fps),
  fps: props.timeline.fps,
});

export const RemotionRoot: React.FC = () => (
  <Composition
    id="MythShort"
    component={MythShort}
    width={W}
    height={H}
    fps={30}
    durationInFrames={300}
    defaultProps={{ timeline: sample as unknown as Timeline, audio: "job/mix.wav" }}
    calculateMetadata={calculateMetadata}
  />
);
