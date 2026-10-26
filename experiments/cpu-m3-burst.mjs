// SPDX-License-Identifier: MIT
// A short low-duty timer workload; no network or user data.
import { performance } from 'node:perf_hooks';
const sleep = (ms) => new Promise(resolve => setTimeout(resolve, ms));
const start = performance.now();
const cpu = process.cpuUsage();
const late = [];
let count = 0;
for (let i = 1; i <= 600; i++) {
  const due = start + i * 10;
  await sleep(Math.max(0, due - performance.now()));
  const now = performance.now();
  late.push(Math.max(0, now - due));
  if (now - due > 500) throw new Error('Worker fell behind; reject the trial');
  const end = now + 2;
  while (performance.now() < end) count++;
}
late.sort((a, b) => a - b);
const used = process.cpuUsage(cpu);
console.log(JSON.stringify({
  callbacks: late.length, seconds: (performance.now() - start) / 1000,
  p95_lateness_ms: late[Math.ceil(late.length * 0.95) - 1],
  max_lateness_ms: late.at(-1), process_cpu_ms: (used.user + used.system) / 1000,
  loop_iterations: count
}));
