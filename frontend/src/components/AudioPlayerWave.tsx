import * as React from "react";
import {
  Background,
  Container,
  WaveformContainer,
  CenterLine,
  ScrollContainer
} from "./styles/AudioPlayerWave.styled";
import AudioWaveForm from "./AudioWaveForm";

/**
  Contains the audio playback waveform and note descriptions of the selected audio
 */
const AudioPlayerWave = () => {
  const meteringArray = [-56.18996810913086, -45.71665573120117, -44.04374694824219, -42.033721923828125, -43.5439567565918, -45.75215530395508, -44.32561492919922, -35.01418685913086, -37.7093391418457, -41.013938903808594, -27.70965003967285, -5.408426761627197, -7.446232795715332, -10.525727272033691, -11.779906272888184, -14.158451080322266, -16.930505752563477, -15.398061752319336, -9.453960418701172, -11.11893367767334, -14.293376922607422, -19.002437591552734, -22.967554092407227, -27.692899703979492, -31.965606689453125, -35.914154052734375, -38.70391082763672, -13.365299224853516, -7.621279716491699, -8.354131698608398, -6.180663108825684, -6.179239749908447, -7.050765037536621, -8.112454414367676, -10.29129695892334, -11.438603401184082, -14.673408508300781, -18.273094177246094, -22.095550537109375, -26.923248291015625, -31.232860565185547, -30.922700881958008, -32.677799224853516, -36.4795036315918, -33.595703125, -24.979080200195312, -9.499576568603516, -9.930668830871582, -8.785672187805176, -8.913267135620117, -10.667296409606934, -12.510384559631348, -14.522135734558105, -12.758369445800781, -13.993314743041992, -16.12727165222168, -19.834674835205078, -24.321590423583984, -27.738304138183594, -30.411237716674805, -33.12632751464844, -35.84364318847656, -39.408321380615234, -5.546092987060547, -5.643970489501953, -7.109328746795654, -8.351934432983398, -9.272828102111816, -8.493043899536133, -10.001343727111816, -11.640403747558594, -13.073893547058105, -14.591792106628418, -45.75215530395508, -44.32561492919922, -35.01418685913086, -37.7093391418457, -41.013938903808594, -27.70965003967285, -5.408426761627197, -7.446232795715332, -10.525727272033691, -11.779906272888184, -14.158451080322266, -16.930505752563477, -15.398061752319336, -9.453960418701172, -11.11893367767334, -14.293376922607422, -19.002437591552734, -22.967554092407227, -27.692899703979492, -31.965606689453125, -35.914154052734375, -38.70391082763672, -13.365299224853516, -7.621279716491699, -8.354131698608398, -6.180663108825684, -6.179239749908447, -7.050765037536621, -8.112454414367676, -10.29129695892334, -11.438603401184082, -14.673408508300781, -18.273094177246094, -22.095550537109375, -26.923248291015625, -31.232860565185547, -30.922700881958008, -32.677799224853516, -36.4795036315918, -33.595703125, -24.979080200195312, -9.499576568603516, -9.930668830871582, -8.785672187805176, -8.913267135620117, -10.667296409606934, -12.510384559631348, -14.522135734558105, -12.758369445800781, -13.993314743041992, -16.12727165222168, -19.834674835205078, -24.321590423583984, -27.738304138183594, -30.411237716674805, -33.12632751464844, -35.84364318847656, -39.408321380615234, -5.546092987060547, -5.643970489501953, -7.109328746795654, -8.351934432983398, -9.272828102111816, -8.493043899536133, -10.001343727111816, -11.640403747558594, -13.073893547058105, -14.591792106628418];

  return (
    <Container>
      <CenterLine source={require("../assets/gradient.png")} />
      <ScrollContainer>
        <WaveformContainer>
          <AudioWaveForm meteringArray={meteringArray} />
        </WaveformContainer>
      </ScrollContainer>
      <Background
        testID="audio-player-background"
        source={require("../assets/player-background.png")}
      />
    </Container>
  );
};

export default AudioPlayerWave;
