export type Platform = "android" | "ios";

export interface DeviceInfo {
  serial: string;
  platform: Platform;
  state: string;
  authorized: boolean;
  model?: string;
  osVersion?: string;
  transport?: "usb" | "wifi" | "emulator" | "wda" | "unknown";
  note?: string;
}

export interface UiNode {
  i: number;
  text?: string;
  desc?: string;
  id?: string;
  cls?: string;
  clickable?: boolean;
  bounds: [number, number, number, number];
  center: [number, number];
}

/** What each backend call reports back so the server can build the standard envelope. */
export interface ActionResult {
  command: string | null;
  exitCode?: number;
  stdout?: string;
  stderr?: string;
  warnings?: string[];
  data?: Record<string, unknown>;
  artifacts?: string[];
  image?: Buffer;
}

export type Key =
  | "BACK" | "HOME" | "RECENTS" | "ENTER" | "TAB" | "DELETE"
  | "POWER" | "VOLUME_UP" | "VOLUME_DOWN" | "WAKEUP";

export interface Backend {
  platform: Platform;
  owns(serial: string): boolean;
  listDevices(): Promise<DeviceInfo[]>;
  screenshot(serial: string): Promise<ActionResult & { image: Buffer }>;
  uiTree(serial: string, maxNodes: number, onlyInteractive: boolean): Promise<ActionResult>;
  tap(serial: string, x: number, y: number, durationMs?: number): Promise<ActionResult>;
  swipe(serial: string, x1: number, y1: number, x2: number, y2: number, durationMs: number): Promise<ActionResult>;
  typeText(serial: string, text: string): Promise<ActionResult>;
  pressKey(serial: string, key: Key): Promise<ActionResult>;
  launchApp(serial: string, appId: string, activity?: string): Promise<ActionResult>;
  openUrl(serial: string, url: string): Promise<ActionResult>;
  currentApp(serial: string): Promise<ActionResult>;
  listApps(serial: string, thirdPartyOnly: boolean): Promise<ActionResult>;
  // Android-only capabilities. iOS backend throws UNSUPPORTED.
  installApp(serial: string, path: string, allowDowngrade: boolean): Promise<ActionResult>;
  uninstallApp(serial: string, appId: string, keepData: boolean): Promise<ActionResult>;
  pushFile(serial: string, local: string, remote: string): Promise<ActionResult>;
  pullFile(serial: string, remote: string, local: string): Promise<ActionResult>;
  logs(serial: string, opts: { tag?: string; level: string; maxLines: number }): Promise<ActionResult>;
  shell(serial: string, command: string): Promise<ActionResult>;
}

export function pngSize(buf: Buffer): { width: number; height: number } | undefined {
  if (buf.length < 24 || buf.readUInt32BE(0) !== 0x89504e47) return undefined;
  return { width: buf.readUInt32BE(16), height: buf.readUInt32BE(20) };
}
