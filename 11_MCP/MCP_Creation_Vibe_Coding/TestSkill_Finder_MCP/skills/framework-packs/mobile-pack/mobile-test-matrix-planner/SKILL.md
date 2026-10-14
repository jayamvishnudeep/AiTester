---
name: mobile-test-matrix-planner
description: >-
  Plans the device, OS and condition matrix for mobile app testing. Use when a QA lead says
  "which phones should we test on", "plan our mobile device coverage", "what about tablets and
  old Android versions", or shares app analytics. Produces a device and OS-version matrix
  based on real user share, plus mobile-specific conditions — interruptions, permissions,
  network changes, low battery, orientation, accessibility settings — and where to run them
  (local devices, emulators or a device cloud).
license: MIT
metadata:
  author: AiTester
  pack: mobile
  version: 1.0.0
---

# Mobile Test Matrix Planner

You choose **the smallest set of devices and conditions that covers the real users**, instead
of testing on whatever phone is on the desk.

## When to use
- A mobile release needs device coverage planned.
- Bugs keep appearing only on certain devices, OS versions or screen sizes.

## Workflow
1. **Start from usage data** — top devices, OS versions, screen sizes and manufacturers from the
   app's analytics or store console. If there is no data, ask for the target markets; do not
   invent shares.
2. **Build the matrix** — cover roughly 80-90% of users: newest and oldest supported OS
   versions, popular manufacturers (Android skins differ), small and large screens, at least one
   tablet if tablets are supported, one low-memory device.
3. **Add mobile conditions** — incoming call or notification mid-flow, app backgrounded and
   restored, permission denied then granted, switching Wi-Fi to mobile data and offline, low
   battery mode, dark mode, large font and screen reader, rotation.
4. **Decide where each runs** — emulators and simulators for fast feedback; real devices or a
   device cloud (BrowserStack, Sauce Labs, Firebase Test Lab, AWS Device Farm) for release.
5. **Assign depth** — full regression on the top devices, smoke on the long tail.

## Output shape
```
## Mobile Test Matrix — <app> v<version>
| Device | OS | Share | Why | Depth | Where |
|--------|----|-------|-----|-------|-------|
| Samsung Galaxy A54 | Android 14 | 12% | top device | full | device cloud |
| iPhone 13 | iOS 17 | 9% | top iOS | full | real device |
| Pixel 4a | Android 11 | 3% | oldest supported | smoke | emulator |
Conditions on top devices: call interruption · offline mode · permission denied · large font
--- HUMAN REVIEW GATE --- "Confirm supported OS versions and the device budget"
```

## Guardrails
- Device shares come from real analytics; never guess them.
- Emulators miss hardware and manufacturer quirks; release testing needs real devices.
- Revisit the matrix every few releases as the user base changes.
