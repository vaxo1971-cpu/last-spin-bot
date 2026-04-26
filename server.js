import express from "express";
import TelegramBot from "node-telegram-bot-api";
import cors from "cors";
import { nanoid } from "nanoid";

const BOT_TOKEN = process.env.BOT_TOKEN;
const PORT = process.env.PORT || 3000;
const PRICE_STARS = Number(process.env.PRICE_STARS || 50);

if (!BOT_TOKEN) {
  console.error("BOT_TOKEN is missing. Add it in Render Environment Variables.");
  process.exit(1);
}

const app = express();
app.use(cors());
app.use(express.json());
const bot = new TelegramBot(BOT_TOKEN, { polling: true });
const codes = new Map();

function createCode(chatId) {
  const code = "LS-" + nanoid(4).toUpperCase() + "-" + nanoid(4).toUpperCase();
  codes.set(code, { chatId, createdAt: Date.now(), used: false });
  return code;
}

bot.onText(/\/start/, async (msg) => {
  const chatId = msg.chat.id;
  await bot.sendMessage(chatId, `🎰 Welcome to Last Spin — Ancient Roulette\n\nTraining simulator only:\n• No real money gambling\n• No cash prizes\n• No withdrawals\n• Virtual balance only\n\nPress the button below to buy one access code.`, {
    reply_markup: { inline_keyboard: [[{ text: `Play — ${PRICE_STARS} Stars`, callback_data: "buy_access" }]] }
  });
});

bot.on("callback_query", async (query) => {
  const chatId = query.message.chat.id;
  if (query.data === "buy_access") {
    await bot.answerCallbackQuery(query.id);
    await bot.sendInvoice(chatId, "Last Spin Access Code", "One-time access code for training roulette simulator. No real gambling, no prizes, no withdrawals.", "last_spin_access", "", "XTR", [{ label: "Access code", amount: PRICE_STARS }]);
  }
});

bot.on("pre_checkout_query", async (query) => {
  await bot.answerPreCheckoutQuery(query.id, true);
});

bot.on("successful_payment", async (msg) => {
  const code = createCode(msg.chat.id);
  await bot.sendMessage(msg.chat.id, `✅ Payment received.\n\nYour one-time access code:\n\n${code}\n\nOpen the roulette website and enter this code.\n\nTraining simulator only. No real money gambling, no prizes, no withdrawals.`);
});

app.get("/", (req, res) => res.json({ ok: true, service: "Last Spin Bot Server" }));
app.post("/validate", (req, res) => {
  const { code } = req.body || {};
  if (!code || !codes.has(code)) return res.status(400).json({ ok: false, error: "Invalid code" });
  const item = codes.get(code);
  if (item.used) return res.status(400).json({ ok: false, error: "Code already used" });
  item.used = true;
  codes.set(code, item);
  return res.json({ ok: true });
});
app.listen(PORT, () => console.log(`Last Spin bot server running on port ${PORT}`));
