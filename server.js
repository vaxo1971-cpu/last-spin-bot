const express = require('express');
const cors = require('cors');
const fs = require('fs');
const path = require('path');
const crypto = require('crypto');
const TelegramBot = require('node-telegram-bot-api');
const { customAlphabet } = require('nanoid');

// --- configuration ---
const BOT_TOKEN = process.env.TELEGRAM_BOT_TOKEN || process.env.BOT_TOKEN;
if (!BOT_TOKEN) throw new Error('TELEGRAM_BOT_TOKEN is required');

const GAME_URL = process.env.GAME_URL || 'https://shiny-axolotl-474a61.netlify.app/';
const PRICE_XTR = Number(process.env.PRICE_XTR || 50);
const OWNER_ID = Number(process.env.OWNER_ID || 0);

const STATE_FILE = process.env.STATE_FILE || path.join(process.cwd(), 'data', 'state.json');
const CODE_SALT = process.env.CODE_SALT || 'change-me';
const CODE_TTL_MS = Number(process.env.CODE_TTL_MS || 60 * 60 * 1000); // 1 hour

const RATE_WINDOW_MS = Number(process.env.RATE_WINDOW_MS || 60 * 1000);
const RATE_LIMIT_PER_USER = Number(process.env.RATE_LIMIT_PER_USER || 5);
const RATE_LIMIT_PER_IP = Number(process.env.RATE_LIMIT_PER_IP || 30);

const CODE_LENGTH = Number(process.env.CODE_LENGTH || 12);
const CODE_ALPHA = 'ABCDEFGHJKLMNPQRSTUVWXYZ23456789';

// --- state ---
function mkdirForFile(fp) {
  fs.mkdirSync(path.dirname(fp), { recursive: true });
}

function loadState() {
  try {
    const raw = fs.readFileSync(STATE_FILE, 'utf8');
    return JSON.parse(raw);
  } catch (e) {
    return { startedUsers: {}, payments: [], codes: [] };
  }
}

function saveState(state) {
  try {
    mkdirForFile(STATE_FILE);
    fs.writeFileSync(STATE_FILE, JSON.stringify(state, null, 2), 'utf8');
  } catch (e) {
    console.error('Failed to save state', e);
  }
}

function hashCode(code) {
  return crypto.createHash('sha256').update(String(CODE_SALT)).update(':').update(String(code)).digest('hex');
}

function now() {
  return Date.now();
}

function addStarted(state, userId) {
  const u = String(userId);
  if (!state.startedUsers[u]) state.startedUsers[u] = { startedAt: now() };
}

function addPayment(state, userId, payment) {
  const u = String(userId);
  state.payments.push({ userId: u, createdAt: now(), ...payment });
}

function issueAccessCode(state, userId, rawCode) {
  const u = String(userId);
  state.codes.push({ userId: u, hash: hashCode(rawCode), createdAt: now(), usedAt: 0 });
}

function cleanExpired(state) {
  const t = now();
  state.codes = state.codes.filter((c) => {
    if (c.usedAt) return true;
    return t - c.createdAt <= CODE_TTL_MS;
  });
}

function consumeCode(state, rawCode) {
  const h = hashCode(rawCode);
  const t = now();
  for (const c of state.codes) {
    if (c.hash !== h) continue;
    if (c.usedAt) {
      // allow validate even if already used, but don't reuse for new sessions
      c.lastValidateAt = t;
      return true;
    }
    c.usedAt = t;
    c.lastValidateAt = t;
    return true;
  }
  return false;
}

function summarize(state) {
  const startedCount = Object.keys(state.startedUsers || {}).length;
  const paidUsers = new Set();
  let paidAmountXtr = 0;
  for (const p of state.payments || []) {
    paidUsers.add(String(p.userId));
    if (p.currency === 'XTR') paidAmountXtr += Number(p.amount || 0);
  }
  const codesIssued = (state.codes || []).length;
  const codesUsed = (state.codes || []).filter((c) => c.usedAt).length;
  return {
    startedCount,
    paymentsCount: (state.payments || []).length,
    paidUsersCount: paidUsers.size,
    paidAmountXtr,
    codesIssued,
    codesUsed,
  };
}

function statsText(state) {
  const s = summarize(state);
  return [
    '📊 Stats',
    '👥 Started: ' + s.startedCount,
    '💳 Payments: ' + s.paymentsCount + ' (paid users: ' + s.paidUsersCount + ')',
    '⭐ Paid amount: ' + s.paidAmountXtr + ' XTR',
    '🎟 Codes issued: ' + s.codesIssued,
    '✅ Codes consumed: ' + s.codesUsed,
  ].join('\n');
}

class RateLimiter {
  constructor(windowMs, max) {
    this.windowMs = windowMs;
    this.max = max;
    this.store = new Map();
  }

  hit(key) {
    const t = now();
    const arr = this.store.get(key) || [];
    const arr2 = arr.filter((x) => t - x < this.windowMs);
    arr2.push(t);
    this.store.set(key, arr2);
    return arr2.length > this.max;
  }
}

const userLimiter = new RateLimiter(RATE_WINDOW_MS, RATE_LIMIT_PER_USER);
const ipLimiter = new RateLimiter(RATE_WINDOW_MS, RATE_LIMIT_PER_IP);

const state = loadState();
cleanExpired(state);
saveState(state);

const cachedCodes = {};

function cacheCode(userId, code) {
  cachedCodes[String(userId)] = { code, createdAt: now() };
}

function takeCode(userId) {
  const obj = cachedCodes[String(userId)];
  if (!obj) return null;
  if (now() - obj.createdAt > 5 * 60 * 1000) {
    delete cachedCodes[String(userId)];
    return null;
  }
  delete cachedCodes[String(userId)];
  return obj.code;
}

async function safeAnswerCbq(id, text) {
  try {
    await bot.answerCallbackQuery(id, { text });
  } catch (e) {
    console.error('answerCbq', e);
  }
}

const bot = new TelegramBot(BOT_TOKEN, { polling: true });
const app = express();
app.use(cors());
app.use(express.json());

const generateCode = customAlphabet(CODE_ALPHA, CODE_LENGTH);

function getPrices() {
  return [
    {
      label: 'Access',
      amount: PRICE_XTR,
    },
  ];
}

bot.onText(/\/start/, async (msg) => {
  const userId = msg.from && msg.from.id;
  if (!userId) return;
  if (userLimiter.hit('start:' + userId)) return;

  addStarted(state, userId);
  saveState(state);

  try {
    await bot.sendMessage(
      msg.chat.id,
      'Last Spin Roulette\n\nTap Pay to buy access, then tap Play.',
      {
        reply_markup: {
          inline_keyboard: [
            [{ text: 'Pay 50⭐', pay: true }],
            [{ text: 'Play', callback_data: 'play' }],
          ],
        },
        protect_content: true,
      }
    );

    await bot.sendInvoice(
      msg.chat.id,
      'Last Spin Roulette',
      'Buy access via Telegram Stars',
      'u' + String(userId) + ':' + String(now()),
      '',
      'XTR',
      getPrices(),
      { protect_content: true }
    );
  } catch (e) {
    console.error('start', e);
  }
});

bot.on('pre_checkout_query', async (pre) => {
  try {
    await bot.answerPreCheckoutQuery(pre.id, true);
  } catch (e) {
    console.error('pre_checkout', e);
  }
});

bot.on('successful_payment', async (msg) => {
  const userId = msg.from && msg.from.id;
  if (!userId) return;
  if (!msg.successful_payment) return;

  const p = msg.successful_payment;
  addPayment(state, userId, {
    currency: p.currency,
    amount: p.total_amount,
    payload: p.invoice_payload,
  });

  const rawCode = generateCode();
  issueAccessCode(state, userId, rawCode);
  saveState(state);

  cacheCode(userId, rawCode);

  try {
    await bot.sendMessage(msg.chat.id, '✅ Payment received. Tap Play to get your code.', {
      reply_markup: { inline_keyboard: [[{ text: 'Play', callback_data: 'play' }]] },
      protect_content: true,
    });
  } catch (e) {
    console.error('paid', e);
  }
});

bot.on('callback_query', async (cbq) => {
  const userId = cbq.from && cbq.from.id;
  if (!userId) return;
  const data = cbq.data || '';

  if (userLimiter.hit('cb:' + userId)) {
    await safeAnswerCbq(cbq.id, 'Too many actions, try later');
    return;
  }

  if (data !== 'play') {
    await safeAnswerCbq(cbq.id, '');
    return;
  }

  cleanExpired(state);
  saveState(state);

  const code = takeCode(userId);
  if (!code) {
    await safeAnswerCbq(cbq.id, 'No ready code yet');
    return;
  }

  const url = GAME_URL + '?code=' + encodeURIComponent(code);

  try {
    await bot.sendMessage(cbq.message.chat.id, '🎮 Your code: ' + code + '\n\n' + url, { protect_content: true });
  } catch (e) {
    console.error('code', e);
  }

  await safeAnswerCbq(cbq.id, 'Link sent');
});

bot.onText(/\/stats/, async (msg) => {
  if (OWNER_ID && msg.from && msg.from.id !== OWNER_ID) return;
  try {
    await bot.sendMessage(msg.chat.id, statsText(state), { protect_content: true });
  } catch (e) {
    console.error('stats', e);
  }
});

function codeFromRequest(req) {
  const b = req.body || {};
  const q = req.query || {};
  const h = req.headers || {};
  return b.code || q.code || h['x-code'] || '';
}

function ipFromReq(req) {
  return req.ip || (req.connection && req.connection.remoteAddress) || 'unknown';
}

app.get('/', (req, res) => {
  res.json({ ok: true, service: 'Last Spin Bot Server' });
});

app.post('/validate', (req, res) => {
  const ip = ipFromReq(req);
  if (ipLimiter.hit('v:' + ip)) {
    return res.status(429).json({ ok: false, error: 'Too many requests' });
  }

  const code = String(codeFromRequest(req));
  if (!code || code.length < 4) return res.status(400).json({ ok: false, error: 'Invalid code' });

  cleanExpired(state);
  const ok = consumeCode(state, code);
  if (ok) saveState(state);
  res.json({ ok });
});

const PORT = process.env.PORT || 3000;
app.listen(PORT, () => {
  console.log('Server listening on', PORT);});
