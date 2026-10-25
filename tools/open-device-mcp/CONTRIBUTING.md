# Contributing

1. `npm install && npm run build && npm test`
2. Add a test in `test/server.test.ts` for any new tool. Extend `test/fake-adb.mjs` if the tool calls new adb commands.
3. New tools go through `wrap()` in `src/server.ts` so they get safety checks, audit logging and the standard result envelope.
4. Only use public, documented interfaces (adb, uiautomator, WebDriverAgent). Do not submit code, assets or text taken from commercial products.
