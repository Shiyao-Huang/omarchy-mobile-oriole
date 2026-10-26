// Bounded resource-control experiment; not an Agent concurrency recommendation.
const {Worker, isMainThread, parentPort} = require('node:worker_threads');
const fs = require('node:fs');
if (!isMainThread) {
  const end = performance.now() + 2000;
  let x = 1;
  while (performance.now() < end) {
    for (let j = 0; j < 10000; ++j) x = (Math.imul(x, 1664525) + 1013904223) | 0;
  }
  parentPort.postMessage({x, affinity:fs.readFileSync("/proc/thread-self/status","utf8").split("\n").find(x=>x.startsWith("Cpus_allowed_list:")).split(":")[1].trim()});
} else {
  const path = fs.readFileSync('/proc/self/cgroup', 'utf8').trim().split('\n').find(x => x.startsWith('0::')).slice(3);
  const dir = '/sys/fs/cgroup' + path;
  const read = name => fs.readFileSync(dir + '/' + name, 'utf8').trim();
  const stats = () => Object.fromEntries(read('cpu.stat').split('\n').map(x => {const [k,v] = x.split(' '); return [k,Number(v)];}));
  const before = stats(), start = performance.now();
  const settings = {cpu_weight:read('cpu.weight'), nice:require('node:os').getPriority(), affinity:fs.readFileSync('/proc/self/status','utf8').split('\n').find(x=>x.startsWith('Cpus_allowed_list:')).split(':')[1].trim()};
  if (settings.cpu_weight !== '25' || settings.nice !== 10 || settings.affinity !== '0-5') throw Error('M2 resource preflight failed: '+JSON.stringify(settings));
  Promise.all(Array.from({length:2}, () => new Promise((resolve,reject) => {
    const w = new Worker(__filename);
    w.on('error',reject);
    let message; w.on('message',value=>{message=value;});
    w.on('exit',code=>code===0 && message?.affinity==='0-5'?resolve(message):reject(Error('worker exit/affinity failure '+code)));
  }))).then(workers => {
    const after=stats(), elapsed_ms=performance.now()-start;
    const result={settings,workers,elapsed_ms,used_cpu_usec:after.usage_usec-before.usage_usec};
    console.log('CPU_M2_JSON='+JSON.stringify(result));
    if (workers.length !== 2 || elapsed_ms > 15000 || result.used_cpu_usec < 100000) process.exitCode=1;
  }).catch(e => {console.error(e);process.exitCode=1;});
}
