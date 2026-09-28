// Node.js 18+. Start the API on this machine first.
// Set ZK_API_TOKEN to the token printed by the server.
const token = process.env.ZK_API_TOKEN;
if (!token) throw new Error('Set ZK_API_TOKEN');
async function call(path, body) {
  const response = await fetch(`http://127.0.0.1:8765${path}`, {
    method: body === undefined ? 'GET' : 'POST',
    headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' },
    body: body === undefined ? undefined : JSON.stringify(body),
    signal: AbortSignal.timeout(15000),
  });
  const result = await response.json();
  if (!response.ok) throw new Error(JSON.stringify(result));
  return result;
}
console.log(await call('/v1/reader'));
console.log(await call('/v1/inventory', { antennas: [1], scan_time: 3 }));
// To stop continuous reading, stop sending inventory requests.
// Never automatically retry POST /v1/write after a timeout.
