// Bounded resource-control experiment; not an Agent concurrency recommendation.
const {Worker, isMainThread, parentPort} = require('node:worker_threads');
const fs = require('node:fs');
if (!isMainThread) {
  const end = performance.now() + 4000;
  let x = 1;
  while (performance.now() < end) {
    for (let j = 0; j < 10000; ++j) x = (Math.imul(x, 1664525) + 1013904223) | 0;
  }
  parentPort.postMessage(x);
} else {
  const path = fs.readFileSync('/proc/self/cgroup', 'utf8').trim().split('\n').find(x => x.startsWith('0::')).slice(3);
  const dir = '/sys/fs/cgroup' + path;
  const read = name => fs.readFileSync(dir + '/' + name, 'utf8').trim();
  const stats = () => Object.fromEntries(read('cpu.stat').split('\n').map(x => {const [k,v] = x.split(' '); return [k,Number(v)];}));
  const before = stats(), start = performance.now();
  const settings = {cpu_max:read('cpu.max'), cpu_weight:read('cpu.weight'), nice:require('node:os').getPriority(), affinity:fs.readFileSync('/proc/self/status','utf8').split('\n').find(x=>x.startsWith('Cpus_allowed_list:')).split(':')[1].trim()};
  if (settings.cpu_max !== '100000 100000' || settings.cpu_weight !== '25' || settings.nice !== 10 || settings.affinity !== '0-7') throw Error('M1 resource preflight failed: '+JSON.stringify(settings));
  Promise.all(Array.from({length:4}, () => new Promise((resolve,reject) => {
    const w = new Worker(__filename);
    w.on('error',reject);
    w.on('exit',code=>code===0?resolve():reject(Error('worker exit '+code)));
  }))).then(() => {
    const after=stats(), elapsed_ms=performance.now()-start;
    const result={settings,workers:4,elapsed_ms,used_cpu_usec:after.usage_usec-before.usage_usec,throttled_periods:after.nr_throttled-before.nr_throttled};
    console.log('CPU_M1_JSON='+JSON.stringify(result));
    if (result.throttled_periods <= 0 || result.used_cpu_usec <= 1000000 || result.used_cpu_usec > elapsed_ms * 1200 + 200000) process.exitCode=1;
  }).catch(e => {console.error(e);process.exitCode=1;});
}
