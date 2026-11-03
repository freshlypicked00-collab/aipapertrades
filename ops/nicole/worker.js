// NINI's task bot: real-time webhook (Cloudflare Worker, owner, Nov 2).
// Telegram sends every tap and message here the moment it happens. The Worker:
//   1. checks the request really comes from Telegram (secret header, derived from the bot token),
//   2. answers a ✅ Done tap at once (NINI sees "Got it" and the button turns into "✅ Done, thanks!"),
//   3. passes the update to GitHub (repository_dispatch "nicole_update"), where ops/nicole_bot.py records it,
//      tells the owner and forwards NINI's messages, within about a minute.
// Secrets (Cloudflare → Worker → Settings → Variables and Secrets): BOT_TOKEN (the bot's token) and GH_TOKEN
// (a GitHub fine-grained token for freshlypicked00-collab/aipapertrades with Contents: Read and write).
// Nothing is stored here.
const REPO = 'freshlypicked00-collab/aipapertrades';

async function hookSecret(token) {
  const d = await crypto.subtle.digest('SHA-256', new TextEncoder().encode('webhook:' + token));
  return [...new Uint8Array(d)].map((b) => b.toString(16).padStart(2, '0')).join('').slice(0, 48);
}

async function tg(env, method, body) {
  return fetch(`https://api.telegram.org/bot${env.BOT_TOKEN}/${method}`, {
    method: 'POST', headers: { 'content-type': 'application/json' }, body: JSON.stringify(body),
  });
}

export default {
  async fetch(request, env, ctx) {
    if (request.method !== 'POST') return new Response('NINI task bot webhook: OK');
    if (request.headers.get('X-Telegram-Bot-Api-Secret-Token') !== await hookSecret(env.BOT_TOKEN)) return new Response('no', { status: 403 });
    const update = await request.json();
    const q = update.callback_query;
    if (q && String(q.data || '').startsWith('done:')) {
      ctx.waitUntil(tg(env, 'answerCallbackQuery', { callback_query_id: q.id, text: 'Got it ✅ Thank you!' }));
      ctx.waitUntil(tg(env, 'editMessageReplyMarkup', { chat_id: q.message.chat.id, message_id: q.message.message_id,
        reply_markup: { inline_keyboard: [[{ text: '✅ Done, thanks!', callback_data: 'noop' }]] } }));
    } else if (q) {
      ctx.waitUntil(tg(env, 'answerCallbackQuery', { callback_query_id: q.id }));
    }
    ctx.waitUntil(fetch(`https://api.github.com/repos/${REPO}/dispatches`, {
      method: 'POST',
      headers: { authorization: `Bearer ${env.GH_TOKEN}`, accept: 'application/vnd.github+json', 'user-agent': 'nini-task-bot', 'content-type': 'application/json' },
      body: JSON.stringify({ event_type: 'nicole_update', client_payload: { update } }),
    }));
    return new Response('ok');   // Telegram only needs a quick 200
  },
};
