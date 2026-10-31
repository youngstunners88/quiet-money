// One world for the whole reel: four year-bars (10, 20, 30, 40) of $500 a month at an assumed 8% a year, compounded
// monthly. Each bar stacks what you paid in (steel) under what it grew (gold). The 10-year bar is a sliver and the 40-year
// bar towers over it, which is the point: the last ten years add about $1 million from $60,000 of new deposits.
// Every move starts on a spoken word (cues are looked up by scene index and word).
import React from "react";
import { useCurrentFrame } from "remotion";
import { arrive, blurIn, countTo, ease, money, pop, prog, useReel } from "../../../src/engine";

const MONTHLY = 500;
const RATE = 0.08 / 12;
const total = (years: number) => (MONTHLY * ((1 + RATE) ** (years * 12) - 1)) / RATE;
const paid = (years: number) => MONTHLY * 12 * years;

const GOLD = "#F5C451";
const STEEL = "#6F7C8E";
const INK = "#FFFFFF";
const DIM = "#8C8C8C";
const ALARM = "#E5484D";

const BASE_Y = 1650;           // the baseline of the chart
const MAX_H = 1000;            // height of the 40-year bar
const BAR_W = 170;
const COLS = [{ y: 10, x: 190 }, { y: 20, x: 430 }, { y: 30, x: 670 }, { y: 40, x: 910 }];
const H = (v: number) => (v / total(40)) * MAX_H;

const font = "Inter, sans-serif";
const abs = (s: React.CSSProperties): React.CSSProperties => ({ position: "absolute", fontFamily: font, ...s });

export const LastTenWorld: React.FC = () => {
  const f = useCurrentFrame();
  const { tl } = useReel();
  const c = (tok: string, scene: number, nth = 1) => tl.cue(tok, nth, scene);
  const END = tl.frames;

  // cue frames: hook 0, ten 1, climb 2, last 3, lesson 4
  const t = {
    slots: c("forty", 0), illus: c("illustration", 0), eight: c("eight", 0), million: c("million", 0),
    y10: c("ten", 1), paid10: c("sixty", 1), grown10: c("ninety", 1), slow: c("slow", 1), quit: c("quit", 1),
    y20: c("twenty", 2), tot20: c("thousand", 2, 1), yours: c("yours", 2), y30: c("thirty", 2), tot30: c("thousand", 2, 3), final: c("final", 2),
    y40: c("forty", 3), dep40: c("deposits", 3, 1), part: c("part", 3), added: c("added", 3), newdep: c("deposits", 3, 2),
    base: c("base", 4), harvest: c("harvested", 4), quitting: c("Quitting", 4), catchW: c("catch", 4), numbers: c("numbers", 4),
    shape: c("shape", 4), time: c("Time", 4), start: c("start", 4), follow: c("Follow", 4),
  };

  const grow = (start: number, dur = 54) => arrive(f, start, dur);
  const bars: Record<number, { p: number; paidH: number; totH: number }> = {};
  const starts: Record<number, number> = { 10: t.y10, 20: t.y20, 30: t.y30, 40: t.y40 };
  for (const col of COLS) {
    const p = f >= starts[col.y] ? grow(starts[col.y], col.y === 40 ? 96 : 54) : 0;
    bars[col.y] = { p, paidH: H(paid(col.y)) * p, totH: H(total(col.y)) * p };
  }

  // headline (what the picture is about right now) and the big number
  const heads: [number, string][] = [
    [0, "$500 A MONTH"], [t.y10, "YEAR 10"], [t.y20, "YEAR 20"], [t.y30, "YEAR 30"], [t.final, "THE LAST 10 YEARS?"],
    [t.y40, "YEAR 40"], [t.added, "THE LAST 10 YEARS"], [t.base, "THE BASE, THEN THE HARVEST"],
    [t.catchW, "REAL LIFE VARIES"], [t.start, "START. STAY IN."], [t.follow, "QUIET MONEY"],
  ];
  let head = heads[0];
  for (const h of heads) if (f >= h[0]) head = h;

  const nums: [number, number][] = [[0, 0], [t.grown10, total(10)], [t.tot20, total(20)], [t.tot30, total(30)], [t.y40 + 40, total(40)]];
  // the big number counts from the previous value to the next on its own cue
  let shown = 0;
  for (let i = 1; i < nums.length; i++) {
    if (f >= nums[i][0]) shown = nums[i][1];
    if (f >= nums[i][0] && f < nums[i][0] + 40) shown = countTo(f, nums[i][0], 40, nums[i - 1][1], nums[i][1]);
  }

  const lastDecade = f >= t.added;
  const showSlots = f >= t.slots;
  const hold = (from: number, to = END) => f >= from && f < to;

  return (
    <div style={abs({ inset: 0, background: "#111214", overflow: "hidden" })}>
      {/* brand mark, small and constant */}
      <div style={abs({ top: 70, left: 0, right: 0, textAlign: "center", fontSize: 36, letterSpacing: 8, color: DIM, fontWeight: 700 })}>QUIET MONEY</div>

      {/* headline */}
      <div key={head[0]} style={abs({ top: 150, left: 0, right: 0, textAlign: "center", fontSize: head[1].length > 20 ? 76 : 110, lineHeight: 1.05, fontWeight: 900, color: head[1] === "REAL LIFE VARIES" ? ALARM : INK, padding: "0 60px", ...blurIn(f, head[0], { dur: 10, rise: 18 }) })}>{head[1]}</div>
      {head[1] === "$500 A MONTH" && <div style={abs({ top: 285, left: 0, right: 0, textAlign: "center", fontSize: 54, fontWeight: 700, color: GOLD, ...blurIn(f, t.slots, { dur: 10 }) })}>FOR 40 YEARS</div>}

      {/* the big number */}
      {f >= t.grown10 && (
        <div style={abs({ top: 400, left: 0, right: 0, textAlign: "center", fontSize: 150, fontWeight: 900, color: GOLD, fontVariantNumeric: "tabular-nums", ...(lastDecade ? { opacity: 0.35 } : {}) })}>{money(shown)}</div>
      )}

      {/* legend */}
      <div style={abs({ left: 70, top: 600, fontSize: 34, fontWeight: 800, color: "#A9B4C4", opacity: prog(f, t.slots, 20) })}>
        <span style={{ display: "inline-block", width: 26, height: 26, background: STEEL, marginRight: 14, verticalAlign: "-3px" }} />YOU PAID IN
        <span style={{ display: "inline-block", width: 26, height: 26, background: GOLD, margin: "0 14px 0 40px", verticalAlign: "-3px" }} /><span style={{ color: GOLD }}>IT GREW</span>
      </div>

      {/* chart: baseline, year labels, ghost slots */}
      <div style={abs({ left: 70, right: 70, top: BASE_Y, height: 3, background: "#2A2A2C", opacity: prog(f, 0, 20) })} />
      {COLS.map((col) => (
        <React.Fragment key={col.y}>
          {showSlots && (
            <div style={abs({ left: col.x - BAR_W / 2, top: BASE_Y - H(total(col.y)), width: BAR_W, height: H(total(col.y)), border: "3px dashed #34363A", borderRadius: 8, opacity: bars[col.y].p > 0 ? 0 : prog(f, t.slots + col.y, 20) * 0.9 })} />
          )}
          {showSlots && <div style={abs({ left: col.x - 100, top: BASE_Y + 20, width: 200, textAlign: "center", whiteSpace: "nowrap", fontSize: 34, fontWeight: 800, color: DIM, ...blurIn(f, t.slots + col.y, { dur: 10 }) })}>{col.y} YEARS</div>}
          {/* the bar: deposits at the bottom, growth above */}
          <div style={abs({ left: col.x - BAR_W / 2, top: BASE_Y - bars[col.y].paidH, width: BAR_W, height: bars[col.y].paidH, background: STEEL, borderRadius: "0 0 8px 8px" })} />
          <div style={abs({ left: col.x - BAR_W / 2, top: BASE_Y - bars[col.y].totH, width: BAR_W, height: Math.max(0, bars[col.y].totH - bars[col.y].paidH), background: GOLD, borderRadius: bars[col.y].paidH > 0 ? "8px 8px 0 0" : 8, opacity: col.y === 40 && f >= t.added ? 1 : (lastDecade && col.y < 40 ? 0.45 : 1) })} />
        </React.Fragment>
      ))}

      {/* labels on the bars */}
      {f >= t.paid10 && <Tag f={f} at={t.paid10} x={190} y={BASE_Y - H(total(10)) - 110} text="$60K PAID IN" color="#A9B4C4" />}
      {f >= t.grown10 && <Tag f={f} at={t.grown10} x={190} y={BASE_Y - H(total(10)) - 64} text="$91K" color={GOLD} />}
      {f >= t.slow && f < t.y20 && <Tag f={f} at={t.slow} x={190} y={BASE_Y - H(total(10)) - 170} text="THIS FEELS SLOW" color={DIM} />}
      {f >= t.quit && f < t.y20 && <Tag f={f} at={t.quit} x={190} y={BASE_Y - H(total(10)) - 230} text="MOST QUIT HERE" color={ALARM} />}
      {f >= t.tot20 && <Tag f={f} at={t.tot20} x={430} y={BASE_Y - H(total(20)) - 64} text="$294K" color={GOLD} />}
      {f >= t.yours && <Tag f={f} at={t.yours} x={430} y={BASE_Y - H(paid(20)) / 2 - 24} text="$120K" color="#0B0B0B" size={34} />}
      {f >= t.tot30 && <Tag f={f} at={t.tot30} x={670} y={BASE_Y - H(total(30)) - 64} text="$745K" color={GOLD} />}
      {f >= t.dep40 && <Tag f={f} at={t.dep40} x={910} y={BASE_Y - H(paid(40)) / 2 - 24} text="$240K" color="#0B0B0B" size={38} />}

      {/* the last ten years: a line at the year-30 level across the year-40 bar, and what sits above it */}
      {f >= t.final && f < t.y40 && (
        <div style={abs({ left: 910 - BAR_W / 2 - 14, top: BASE_Y - H(total(40)) - 70, width: BAR_W + 28, textAlign: "center", fontSize: 46, fontWeight: 900, color: GOLD, ...pop(f, t.final) })}>?</div>
      )}
      {f >= t.added && (
        <>
          <div style={abs({ left: 70, right: 70, top: BASE_Y - H(total(30)), height: 0, borderTop: "3px dashed #FFFFFF", opacity: prog(f, t.added, 14) })} />
          <div style={abs({ left: 70, top: BASE_Y - H(total(30)) - 300, width: 700, fontSize: 92, fontWeight: 900, color: GOLD, lineHeight: 1, whiteSpace: "nowrap", ...blurIn(f, c("dollars", 3), { dur: 10 }) })}>+$1,000,000</div>
          <div style={abs({ left: 70, top: BASE_Y - H(total(30)) - 195, width: 700, fontSize: 40, fontWeight: 800, color: INK, lineHeight: 1.1, ...blurIn(f, c("sixty", 3), { dur: 10 }) })}>FROM $60K OF NEW DEPOSITS</div>
        </>
      )}

      {/* the lesson */}
      {f >= t.base && f < t.harvest && <Bracket f={f} at={t.base} x1={105} x2={755} y={BASE_Y + 120} text="THE BASE" />}
      {f >= t.harvest && f < t.quitting && <Bracket f={f} at={t.harvest} x1={825} x2={995} y={BASE_Y + 120} text="HARVEST" />}
      {f >= t.quitting && f < t.catchW && (
        <div style={abs({ left: 70, top: BASE_Y + 100, width: 940, textAlign: "center", fontSize: 44, whiteSpace: "nowrap", fontWeight: 900, color: ALARM, ...blurIn(f, t.quitting, { dur: 10 }) })}>QUIT AT YEAR 10: $91K, NOT $1.7M</div>
      )}
      {f >= t.catchW && f < t.shape && (
        <>
          <div style={abs({ left: 910 - BAR_W / 2 - 40, top: BASE_Y - H(total(40)) - 70, width: BAR_W + 80, height: 140, border: "3px dashed " + ALARM, borderRadius: 12, opacity: prog(f, t.catchW, 12) })} />
          <div style={abs({ left: 70, top: BASE_Y + 100, width: 940, textAlign: "center", fontSize: 36, whiteSpace: "nowrap", fontWeight: 800, color: DIM, ...blurIn(f, c("fees", 4), { dur: 10 }) })}>RETURNS BOUNCE · FEES TAKE A CUT · INFLATION</div>
        </>
      )}
      {f >= t.shape && f < t.follow && (
        <div style={abs({ left: 70, top: BASE_Y + 100, width: 940, textAlign: "center", fontSize: 50, fontWeight: 900, color: INK, ...blurIn(f, t.shape, { dur: 10 }) })}>{f >= t.start ? "TIME DOES THE HEAVY LIFTING" : "THE SHAPE HOLDS"}</div>
      )}
      {f >= t.follow && (
        <div style={abs({ left: 70, top: BASE_Y + 100, width: 940, textAlign: "center", fontSize: 34, whiteSpace: "nowrap", fontWeight: 800, color: GOLD, ...blurIn(f, t.follow, { dur: 10 }) })}>THE MONEY RULES SCHOOL NEVER TAUGHT YOU</div>
      )}
      {f >= t.illus && f < t.y10 && (
        <div style={abs({ left: 70, top: BASE_Y + 100, width: 940, textAlign: "center", fontSize: 42, fontWeight: 800, color: DIM, ...blurIn(f, t.illus, { dur: 10 }) })}>{f >= t.eight ? "ASSUMES 8% A YEAR · NOT A PROMISE" : "AN ILLUSTRATION, NOT A PROMISE"}</div>
      )}
    </div>
  );
};

const Tag: React.FC<{ f: number; at: number; x: number; y: number; text: string; color: string; size?: number }> = ({ f, at, x, y, text, color, size = 40 }) => (
  <div style={abs({ left: x - 170, top: y, width: 340, textAlign: "center", whiteSpace: "nowrap", fontSize: size, fontWeight: 900, color, ...blurIn(f, at, { dur: 10, rise: 10 }) })}>{text}</div>
);

const Bracket: React.FC<{ f: number; at: number; x1: number; x2: number; y: number; text: string }> = ({ f, at, x1, x2, y, text }) => (
  <div style={abs({ left: x1, top: y, width: x2 - x1, textAlign: "center", fontSize: 50, fontWeight: 900, color: GOLD, borderTop: "4px solid " + GOLD, paddingTop: 14, ...blurIn(f, at, { dur: 10 }) })}>{text}</div>
);
