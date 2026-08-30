# Security Policy & Responsible Use

CE Agent CLI is a **dual-use** tool: it reads and writes another process's memory
and can drive a debugger. It exists for **local debugging, security research, and
process introspection** — not for cheating or for tampering with software you do
not control.

## Authorised use only

Attach to and analyse only processes that **you own or have explicit written
permission to inspect**. Do not use this tool to:

- bypass, disable, or tamper with anti-cheat systems, DRM, or licensing;
- modify online or multiplayer games or services;
- violate any software's terms of service, or any applicable law.

You are responsible for how you use it.

## Operational notes

- Live memory operations require administrator privileges by design.
- The Cheat Engine bridge listens on a local named pipe; only enable it in a
  trusted local environment.
- The automated test suite runs without administrator rights and without a live
  target process.

## Reporting a vulnerability

Please **do not open a public issue** for security problems. Email the maintainer
at **liaosens991@gmail.com** with details and reproduction steps; you can expect
an acknowledgement within a few days.
