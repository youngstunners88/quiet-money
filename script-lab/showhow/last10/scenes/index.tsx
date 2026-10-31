import React from "react";
import type { SceneMap } from "../../../src/engine/Stage";
import { LastTenWorld } from "./LastTenWorld";

// Every scene draws the same chart from the reel's frame, so the change between scenes is one continuous picture.
const World: React.FC = () => <LastTenWorld />;

export const scenes: SceneMap = { hook: World, ten: World, climb: World, last: World, lesson: World };
