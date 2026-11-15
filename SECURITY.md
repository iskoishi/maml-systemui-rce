# Security Policy

This repository documents a security research finding for **research and educational purposes only**. It contains a **harmless** proof-of-concept (a single `Log.d` call from `com.android.systemui`) and does **not** include any working exploit, delivery chain, or attack tooling.

## Reporting a vulnerability

If you are a vendor or a researcher and believe you have found a related issue, or need to reach the author about this finding, please open an issue on this repository or contact via the author profile.

## Disclosure context

- **Finding**: MIUI / HyperOS lockscreen MAML (`<MethodCommand>`) reflection execution in `com.android.systemui` (uid 1000)
- **Real-device verified**: HyperOS OS2.0.6.0.UMQCNXM (Android 14, SDK 34)
- **Static cross-version check**: HyperOS OS4.0.6.0.XPNCNXM (Android 17, SDK 37) — not real-device verified
- **Attack prerequisite (proven delivery path)**: shell access to place the theme resource and trigger application
- **Boundary**: no root; SELinux domain remains `system_app`
- **Status**: unpatched as of 2026-11-14
