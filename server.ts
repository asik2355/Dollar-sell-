import express from 'express';
import TelegramBot from 'node-telegram-bot-api';
import path from 'path';
import { createServer as createViteServer } from 'vite';
import { initializeApp } from "firebase/app";
import { getFirestore, doc, getDoc, setDoc, collection, getDocs } from "firebase/firestore";

// Firebase configuration provided by user
const firebaseConfig = {
  apiKey: "AIzaSyDdCBhHtz0HsY2tFDFl3UYq2mog7aEVZ1A",
  authDomain: "rafsun-ravid.firebaseapp.com",
  projectId: "rafsun-ravid",
  storageBucket: "rafsun-ravid.firebasestorage.app",
  messagingSenderId: "319320602603",
  appId: "1:319320602603:web:ef539defe63040d5540bae",
  measurementId: "G-6CSGF67YD5"
};

// Initialize Firebase
const firebaseApp = initializeApp(firebaseConfig);
const db = getFirestore(firebaseApp);

const token = '8716745260:AAGPEuKxQgK3Vv7kTQ5vmlup89acZ9trLNQ';
// Disabling Node.js bot polling to avoid conflict with bot.py
// const bot = new TelegramBot(token, { polling: true });

// Dummy bot object to prevent crashes in other parts of server.ts if called
const bot = {
  sendMessage: async () => {},
  deleteMessage: async () => {},
  editMessageText: async () => {},
  sendPhoto: async () => {},
  editMessageReplyMarkup: async () => {},
  onText: () => {},
  on: () => {},
  answerCallbackQuery: () => {}
} as any;

interface Settings {
  admins: number[];
  exchangeRate: number;
  adminGroupId: number | null;
  depositMethods: { name: string; address: string }[];
  withdrawalMethods: string[];
  supportUsername: string;
}

const PERMANENT_ADMIN_IDS = [8716745260, 8197284774];

let settings: Settings = {
  admins: [...PERMANENT_ADMIN_IDS],
  exchangeRate: 110,
  adminGroupId: null,
  depositMethods: [],
  withdrawalMethods: [],
  supportUsername: 'admin',
};

// Tracking last message to keep chat clean
const lastMessageIds: Record<number, number> = {};

async function safeSendMessage(chatId: number, text: string, options: any = {}) {
  // Delete previous bot message if exists
  if (lastMessageIds[chatId]) {
    try {
      await bot.deleteMessage(chatId, lastMessageIds[chatId].toString());
    } catch (e) { /* ignored */ }
  }
  
  const sentMsg = await bot.sendMessage(chatId, text, options);
  lastMessageIds[chatId] = sentMsg.message_id;
  return sentMsg;
}

async function safeEditMessage(chatId: number, messageId: number, text: string, options: any = {}) {
  try {
    const editedMsg = await bot.editMessageText(text, { chat_id: chatId, message_id: messageId, ...options });
    // Update tracking if return is a message object
    if (typeof editedMsg !== 'boolean') {
      lastMessageIds[chatId] = editedMsg.message_id;
    }
    return editedMsg;
  } catch (e) {
    // If edit fails (e.g. same content), try sending new message
    return await safeSendMessage(chatId, text, options);
  }
}

// Helper for unicode bold (Sans-Serif Bold)
const toUnicodeBold = (text: string) => {
  const chars: Record<string, string> = {
    'A': '𝗔', 'B': '𝗕', 'C': '𝗖', 'D': '𝗗', 'E': '𝗘', 'F': '𝗙', 'G': '𝗚', 'H': '𝗛', 'I': '𝗜', 'J': '𝗝', 'K': '𝗞', 'L': '𝗟', 'M': '𝗠', 'N': '𝗡', 'O': '𝗢', 'P': '𝗣', 'Q': '𝗤', 'R': '𝗥', 'S': '𝗦', 'T': '𝗧', 'U': '𝗨', 'V': '𝗩', 'W': '𝗪', 'X': '𝗫', 'Y': '𝗬', 'Z': '𝗭',
    'a': '𝗮', 'b': '𝗯', 'c': '𝗰', 'd': '𝗱', 'e': '𝗲', 'f': '𝗳', 'g': '𝗴', 'h': '𝗵', 'i': '𝗶', 'j': '𝗷', 'k': '𝗸', 'l': '𝗹', 'm': '𝗺', 'n': '𝗻', 'o': '𝗼', 'p': '𝗽', 'q': '𝗾', 'r': '𝗿', 's': '𝘀', 't': '𝘁', 'u': '𝘂', 'v': '𝘃', 'w': '𝗪', 'x': '𝘅', 'y': '𝘆', 'z': '𝘇',
    '0': '𝟬', '1': '𝟭', '2': '𝟮', '3': '𝟯', '4': '𝟰', '5': '𝟱', '6': '𝟲', '7': '𝟳', '8': '𝟴', '9': '𝟵'
  };
  return Array.from(text).map(c => chars[c] || c).join('');
};

const bold = (text: string) => toUnicodeBold(text.toUpperCase());

// Normalization helper to convert unicode bold back to ASCII for logic
const normalizeText = (text: string) => {
  const chars: Record<string, string> = {
    '𝗔': 'A', '𝗕': 'B', '𝗖': 'C', '𝗗': 'D', '𝗘': 'E', '𝗙': 'F', '𝗚': 'G', '𝗛': 'H', '𝗜': 'I', '𝗝': 'J', '𝗞': 'K', '𝗟': 'L', '𝗠': 'M', '𝗡': 'N', '𝗢': 'O', '𝗣': 'P', '𝗤': 'Q', '𝗥': 'R', '𝗦': 'S', '𝗧': 'T', '𝗨': 'U', '𝗩': 'V', '𝗪': 'W', '𝗫': 'X', '𝗬': 'Y', '𝗭': 'Z',
    '𝗮': 'A', '𝗯': 'B', '𝗰': 'C', '𝗱': 'D', '𝗲': 'E', '𝗳': 'F', '𝗴': 'G', '𝗵': 'H', '𝗶': 'I', '𝗷': 'J', '𝗸': 'K', '𝗹': 'L', '𝗺': 'M', '𝗻': 'N', '𝗼': 'O', '𝗽': 'P', '𝗾': 'Q', '𝗿': 'R', '𝘀': 'S', '𝘁': 'T', '𝘂': 'U', '𝘃': 'V', '𝘄': 'W', '𝘅': 'X', '𝘆': 'Y', '𝘇': 'Z',
    '𝟬': '0', '𝟭': '1', '𝟮': '2', '𝟯': '3', '𝟰': '4', '𝟱': '5', '𝟲': '6', '𝟳': '7', '𝟴': '8', '𝟵': '9'
  };
  return Array.from(text).map(c => chars[c] || c).join('').toUpperCase();
};

// Firestore Syncing
async function loadSettings() {
  try {
    const docRef = doc(db, "bot_settings", "global");
    const docSnap = await getDoc(docRef);
    if (docSnap.exists()) {
      settings = docSnap.data() as Settings;
      // Ensure all permanent admins are always in the list
      PERMANENT_ADMIN_IDS.forEach(id => {
        if (!settings.admins.includes(id)) {
          settings.admins.push(id);
        }
      });
    } else {
      await saveSettings();
    }
  } catch (e) {
    console.error("Error loading settings from Firestore", e);
  }
}

async function saveSettings() {
  try {
    await setDoc(doc(db, "bot_settings", "global"), settings);
  } catch (e) {
    console.error("Error saving settings to Firestore", e);
  }
}

async function trackUser(userId: number, username?: string) {
  try {
    await setDoc(doc(db, "bot_users", userId.toString()), {
      userId,
      username: username || 'Unknown',
      lastSeen: new Date().toISOString()
    });
  } catch (e) {
    console.error("Error tracking user", e);
  }
}

async function trackOrder(userId: number, data: any) {
  try {
    await setDoc(doc(collection(db, "bot_orders")), {
      userId,
      amount: data.amount,
      totalBdt: data.totalBdt,
      timestamp: new Date().toISOString(),
      status: 'PENDING'
    });
  } catch (e) {
    console.error("Error tracking order", e);
  }
}

async function getStats() {
  const usersSnap = await getDocs(collection(db, "bot_users"));
  const ordersSnap = await getDocs(collection(db, "bot_orders"));
  return {
    totalUsers: usersSnap.size,
    totalOrders: ordersSnap.size
  };
}

// User states to track flow
const userStates: Record<number, { 
  step: string; 
  data: any;
}> = {};

function isAdminUser(userId: number) {
  return PERMANENT_ADMIN_IDS.includes(userId) || settings.admins.includes(userId);
}

// Keyboards
function getMainMenu(userId: number) {
  const keyboard = [
    [{ text: bold('💵 Sell Dollar') }],
    [{ text: bold('☎️ Support') }]
  ];

  if (isAdminUser(userId)) {
    keyboard[1].push({ text: bold('⚙️ Admin Panel') });
  }

  return {
    reply_markup: {
      keyboard: keyboard,
      resize_keyboard: true
    }
  };
}

bot.onText(/\/start/, async (msg) => {
  if (msg.chat.type !== 'private') return;
  const chatId = msg.chat.id;
  const userId = msg.from?.id;
  if (!userId) return;

  await trackUser(userId, msg.from.username);
  await loadSettings();

  const welcomeText = `𝗔𝗦𝗦𝗔𝗠𝗨𝗟𝗔𝗜𝗞𝗨𝗠 ❤️\n` +
    `𝗜'𝗠 ${bold('𝗥𝗔𝗙𝗦𝗨𝗡 𝗥𝗔𝗩𝗜𝗗')}\n` +
    `${bold('𝗔𝗗𝗠𝗜𝗡 𝗢𝗙 𝗨𝗡Ｉ𝗩𝗘𝗥𝗦𝗘 𝗘𝗫𝗖𝗛𝗔𝗡𝗚𝗘𝗥')}`;

  safeSendMessage(chatId, welcomeText, getMainMenu(userId));
});

bot.on('message', async (msg) => {
  try {
    if (msg.chat.type !== 'private') return;
    const chatId = msg.chat.id;
    const userId = msg.from?.id;
    if (!userId || msg.text?.startsWith('/')) return;

    const rawText = msg.text || '';
    const cleanText = normalizeText(rawText);
    const state = userStates[userId];

    console.log(`[Message] From: ${userId}, Text: ${rawText}, Normalized: ${cleanText}`);

    // Handle Menu Layout Buttons
    if (cleanText.includes('SELL DOLLAR')) {
      userStates[userId] = { step: 'SELECT_DEPOSIT_METHOD', data: {} };
      const methods = settings.depositMethods.map(m => [{ text: `💳 ${bold(m.name)}`, callback_data: `deposit_${m.name}` }]);
      safeSendMessage(chatId, `🏦 ${bold('Choose How You Want To Pay')}\n\n👇 ${bold('Select where you will send your money')}:`, {
        reply_markup: { inline_keyboard: [...methods, [{ text: `🔙 ${bold('Back to Menu')}`, callback_data: 'menu_main' }]] }
      });
      return;
    }

    if (cleanText.includes('SUPPORT')) {
      const firstName = msg.from?.first_name || 'User';
      const supportMsg = `═《  ${bold('𝗦𝗨𝗣𝗣𝗢𝗥𝗧')} 》═\n` +
        `━━━━━━━━━━━\n` +
        `👋 Hello, ${bold(firstName)}!\n` +
        `💬 Welcome to support panel\n` +
        `➤ Tell me how can I help you\n` +
        `➤ Tap support button\n` +
        `➤ To contact admin!\n` +
        `━━━━━━━━━━━`;
      
      safeSendMessage(chatId, supportMsg, {
        reply_markup: { 
          inline_keyboard: [
            [{ text: `☎️ ${bold('SUPPORT')}`, url: `https://t.me/${settings.supportUsername}` }],
            [{ text: `🔙 ${bold('Back to Menu')}`, callback_data: 'menu_main' }]
          ] 
        }
      });
      return;
    }

    if (cleanText.includes('ADMIN PANEL')) {
      if (!isAdminUser(userId)) {
        safeSendMessage(chatId, `❌ ${bold('𝗔𝗰𝗰𝗲𝘀𝘀 𝗗𝗲𝗻𝗶𝗲𝗱. 𝗔𝗱𝗺𝗶𝗻𝘀 𝗢𝗻𝗹𝘆.')}`);
        return;
      }
      showAdminPanel(chatId);
      return;
    }

    if (!state) return;

    // Handle Input for steps
    switch (state.step) {
      case 'ENTER_AMOUNT':
        const amount_v = parseFloat(rawText);
        if (isNaN(amount_v) || amount_v <= 0) {
          safeSendMessage(chatId, `⚠️ ${bold('𝗜𝗡𝗩𝗔𝗟𝗜𝗗 𝗜𝗡𝗣𝗨𝗧. 𝗣𝗟𝗘𝗔𝗦𝗘 𝗘𝗡𝗧𝗘𝗥 𝗔 𝗩𝗔𝗟𝗜𝗗 𝗨𝗦𝗗 𝗔𝗠𝗢𝗨𝗡𝗧.')}`);
        } else {
          state.data.amount = amount_v;
          state.data.totalBdt = amount_v * settings.exchangeRate;
          state.step = 'AWAIT_TX_ID';
          
          const pxt_msg = `📋 ${bold('𝗣𝗔𝗬𝗠𝗘𝗡𝗧 𝗗𝗘𝗧𝗔𝗜𝗟𝗦')}\n\n` +
            `💰 ${bold('𝗦𝗘𝗡𝗗 𝗔𝗠𝗢𝗨𝗡𝗧')}: ${state.data.amount} dollar\n` +
            `📉 ${bold('𝗥𝗔𝗧𝗘')}: ${bold('𝟭 𝗨𝗦𝗗 = ' + settings.exchangeRate + ' 𝗕𝗗𝗧')}\n` +
            `${bold('𝗬𝗢𝗨 𝗥𝗘𝗖𝗘𝗜𝗩𝗘𝗗')} = ${state.data.totalBdt} bdt\n` +
            `🏦 ${bold('𝗧𝗥𝗔𝗡𝗦𝗙𝗘𝗥 𝗧𝗢')}: ${bold(state.data.depositMethod.name)}\n` +
            `📍 ${bold('𝗪𝗔𝗟𝗟𝗘𝗧/𝗔𝗗𝗗𝗥𝗘𝗦𝗦')}: \`${state.data.depositMethod.address}\`\n\n` +
            `🚀 ${bold('𝗦𝗘𝗡𝗗 𝗧𝗛𝗘 𝗗𝗢𝗟𝗟𝗔𝗥 𝗔𝗡𝗗 𝗧𝗛𝗘𝗡 𝗣𝗥𝗢𝗩𝗜𝗗𝗘 𝗧𝗛𝗘 𝗧𝗥𝗔𝗡𝗦𝗔𝗖𝗧𝗜𝗢𝗡 𝗜𝗗 𝗧𝗢 𝗣𝗥𝗢𝗖𝗘𝗘𝗗')}:`;

          safeSendMessage(chatId, pxt_msg, { 
            parse_mode: 'Markdown',
            reply_markup: {
              inline_keyboard: [
                [
                  { text: `📝 ${bold('𝗧𝗥𝗔𝗡𝗦𝗔𝗖𝗧𝗜𝗢𝗡 𝗜𝗗')}`, callback_data: 'none' },
                  { text: `➡ ${bold('𝗡𝗘𝗫𝗧 𝗦𝗖𝗥𝗘𝗘𝗡𝗦𝗛𝗢𝗧')}`, callback_data: 'none' }
                ]
              ]
            }
          });
        }
        break;

      case 'AWAIT_TX_ID':
        state.data.txId = rawText || 'Manual Entry';
        state.step = 'AWAIT_SCREENSHOT';
        safeSendMessage(chatId, `✅ ${bold('𝗧𝗥𝗔𝗡𝗦𝗔𝗖𝗧𝗜𝗢𝗡 𝗜𝗗 𝗥𝗘𝗖𝗘𝗜𝗩𝗘𝗗!')}\n\n📸 ${bold('𝗡𝗢𝗪 𝗣𝗟𝗘𝗔𝗦𝗘 𝗨𝗣𝗟𝗢𝗔𝗗 𝗧𝗛𝗘 𝗣𝗔𝗬𝗠𝗘𝗡𝗧 𝗦𝗖𝗥𝗘𝗘𝗡𝗦𝗛𝗢𝗧')} 👇`, {
          reply_markup: {
            inline_keyboard: [
              [
                { text: `✅ ${bold('𝗧𝗥𝗔𝗡𝗦𝗔𝗖𝗧𝗜𝗢𝗡 𝗜𝗗')}`, callback_data: 'none' },
                { text: `📸 ${bold('𝗡𝗘𝗫𝗧 𝗦𝗖𝗥𝗘𝗘𝗡𝗦𝗛𝗢𝗧')}`, callback_data: 'none' }
              ]
            ]
          }
        });
        break;

      case 'AWAIT_SCREENSHOT':
        if (msg.photo || msg.document || rawText) {
          state.data.screenshotId = msg.photo ? msg.photo[msg.photo.length - 1].file_id : (msg.document?.file_id || null);
          if (!state.data.screenshotId && rawText) state.data.manualProof = rawText;
          state.step = 'SELECT_WITHDRAWAL_METHOD';
          const wMethods_opts = settings.withdrawalMethods.map(m => [{ text: `🏧 ${bold(m)}`, callback_data: `withdraw_${m}` }]);
          safeSendMessage(chatId, `🏦 ${bold('𝗥𝗘𝗖𝗘𝗜𝗩𝗘 𝗠𝗢𝗡𝗘𝗬 𝗩𝗜𝗔')}\n\n👇 ${bold('𝗦𝗘𝗟𝗘𝗖𝗧 𝗪𝗛𝗘𝗥𝗘 𝗬𝗢𝗨 𝗪𝗔𝗡𝗧 𝗧𝗢 𝗥𝗘𝗖𝗘𝗜𝗩𝗘 𝗬𝗢𝗨𝗥 𝗙𝗨𝗡𝗗𝗦')}:`, {
            reply_markup: { inline_keyboard: wMethods_opts }
          });
        }
        break;

      case 'ENTER_ACCOUNT_NUMBER':
        state.data.accountNumber = rawText;
        submitRequest(chatId, userId, state.data, msg.from?.first_name || 'User');
        trackOrder(userId, state.data);
        delete userStates[userId];
        safeSendMessage(chatId, `⏳ ${bold('𝗥𝗘𝗤𝗨𝗘𝗦𝗧 𝗦𝗨𝗕𝗠𝗜𝗧𝗧𝗘𝗗')}\n\n✅ ${bold('𝗣𝗟𝗘𝗔𝗦𝗘 𝗦𝗧𝗔𝗬 𝗢𝗡𝗟𝗜𝗡𝗘. 𝗬𝗢𝗨𝗥 𝗣𝗔𝗬𝗠𝗘𝗡𝗧 𝗪𝗜𝗟𝗟 𝗕𝗘 𝗦𝗘𝗡𝗧 𝗧𝗢 𝗬𝗢𝗨𝗥 𝗔𝗖𝗖𝗢𝗨𝗡𝗧 𝗦𝗛𝗢𝗥𝗧𝗟𝗬 𝗪𝗜𝗧𝗛𝗜𝗡 𝗔 𝗙𝗘𝗪 𝗠𝗜𝗡𝗨𝗧𝗘𝗦.')}`, getMainMenu(userId));
        break;

      case 'ADMIN_SET_RATE':
        const newRate = parseFloat(rawText);
        if (!isNaN(newRate)) {
          settings.exchangeRate = newRate;
          await saveSettings();
          safeSendMessage(chatId, `✅ ${bold('𝗘𝗫𝗖𝗛𝗔𝗡𝗚𝗘 𝗥𝗔𝗧𝗘 𝗨𝗣𝗗𝗔𝗧𝗘𝗗 𝗦𝗨𝗖𝗖𝗘𝗦𝗦𝗙𝗨𝗟𝗟𝗬!')}`);
          delete userStates[userId];
          showAdminPanel(chatId);
        }
        break;

      case 'ADMIN_ADD_METHOD_NAME':
        state.data.name = rawText;
        state.step = 'ADMIN_ADD_METHOD_ADDRESS';
        safeSendMessage(chatId, `📍 ${bold('𝗘𝗡𝗧𝗘𝗥 𝗔𝗗𝗗𝗥𝗘𝗦𝗦/𝗡𝗨𝗠𝗕𝗘𝗥 𝗙𝗢𝗥')} ${bold(state.data.name)}:`, {
          reply_markup: { inline_keyboard: [[{ text: `🔙 ${bold('𝗕𝗔𝗖𝗞')}`, callback_data: 'admin_manage_dep' }]] }
        });
        break;

      case 'ADMIN_ADD_METHOD_ADDRESS':
        settings.depositMethods.push({ name: state.data.name, address: rawText });
        await saveSettings();
        safeSendMessage(chatId, `✅ ${bold('𝗠𝗘𝗧𝗛𝗢𝗗 𝗔𝗗𝗗𝗘𝗗 𝗦𝗨𝗖𝗖𝗘𝗦𝗦𝗙𝗨𝗟𝗟𝗬!')}`);
        delete userStates[userId];
        showAdminPanel(chatId);
        break;

      case 'ADMIN_ADD_USER':
        const newAdminId = parseInt(rawText);
        if (!isNaN(newAdminId)) {
          if (!settings.admins.includes(newAdminId)) {
            settings.admins.push(newAdminId);
            await saveSettings();
            safeSendMessage(chatId, `✅ ${bold('𝗨𝘀𝗲𝗿')} ${newAdminId} ${bold('𝗔𝗱𝗱𝗲𝗱 𝗮𝘀 𝗔𝗱𝗺𝗶𝗻!')}`);
          } else {
            safeSendMessage(chatId, `ℹ️ ${bold('𝗨𝘀𝗲𝗿 𝗶𝘀 𝗮𝗹𝗿𝗲𝗮𝗱𝘆 𝗮𝗻 𝗔𝗱𝗺𝗶𝗻.')}`);
          }
          delete userStates[userId];
          showAdminPanel(chatId);
        }
        break;

      case 'ADMIN_ADD_WITHDRAW_NAME':
        settings.withdrawalMethods.push(rawText);
        await saveSettings();
        safeSendMessage(chatId, `✅ ${bold('𝗪𝗜𝗧𝗛𝗗𝗥𝗔𝗪𝗔𝗟 𝗠𝗘𝗧𝗛𝗢𝗗')} ${bold(rawText)} ${bold('𝗔𝗗𝗗𝗘𝗗!')}`);
        delete userStates[userId];
        showAdminPanel(chatId);
        break;

      case 'ADMIN_SET_SUPPORT':
        const username_new = rawText.replace('@', '');
        settings.supportUsername = username_new;
        await saveSettings();
        safeSendMessage(chatId, `✅ ${bold('𝗦𝗨𝗣𝗣𝗢𝗥𝗧 𝗨𝗦𝗘𝗥𝗡𝗔𝗠𝗘 𝗨𝗣𝗗𝗔𝗧𝗘𝗗 𝗧𝗢')} @${username_new}`);
        delete userStates[userId];
        showAdminPanel(chatId);
        break;

      case 'ADMIN_SET_GROUP':
        const gid_new = parseInt(rawText);
        if (!isNaN(gid_new)) {
          settings.adminGroupId = gid_new;
          await saveSettings();
          safeSendMessage(chatId, `✅ ${bold('𝗔𝗗𝗠𝗜𝗡 𝗚𝗥𝗢𝗨𝗣 𝗜𝗗 𝗨𝗣𝗗𝗔𝗧𝗘𝗗 𝗧𝗢')} ${gid_new}`);
          delete userStates[userId];
          showAdminPanel(chatId);
        } else {
          safeSendMessage(chatId, `⚠️ ${bold('𝗜𝗡𝗩𝗔𝗟𝗜𝗗 𝗜𝗡𝗣𝗨𝗧. 𝗣𝗟𝗘𝗔𝗦𝗘 𝗘𝗡𝗧𝗘𝗥 𝗔 𝗡𝗨𝗠𝗘𝗥𝗜𝗖 𝗖𝗛𝗔𝗧 𝗜𝗗.')}`);
        }
        break;

      case 'ADMIN_BROADCAST':
        broadcastMessage(msg, chatId);
        delete userStates[userId];
        break;
    }
  } catch (e) {
    console.error('Error in message handler:', e);
  }
});

// Broadcast Logic
async function broadcastMessage(originalMsg: TelegramBot.Message, adminChatId: number) {
  try {
    const querySnapshot = await getDocs(collection(db, "bot_users"));
    let successCount = 0;
    let failCount = 0;

    for (const doc of querySnapshot.docs) {
      const userData = doc.data();
      if (userData.userId === adminChatId) continue;
      try {
        await bot.copyMessage(userData.userId, adminChatId, originalMsg.message_id);
        successCount++;
      } catch (e) {
        failCount++;
      }
    }
    safeSendMessage(adminChatId, `✅ ${bold('𝗕𝗥𝗢𝗔𝗗𝗖𝗔𝗦𝗧 𝗙𝗜𝗡𝗜𝗦𝗛𝗘𝗗')}\n\n${bold('𝗦𝗘𝗡𝗧 𝗧𝗢')}: ${successCount}\n${bold('𝗙𝗔𝗜𝗟𝗘𝗗')}: ${failCount}`, getMainMenu(adminChatId));
  } catch (e) {
    safeSendMessage(adminChatId, `❌ ${bold('𝗕𝗥𝗢𝗔𝗗𝗖𝗔𝗦𝗧 𝗙𝗔𝗜𝗟𝗘𝗗')}: ${e}`);
  }
}

// Admin Panel Keyboard
async function showAdminPanel(chatId: number) {
  const stats = await getStats();
  const msgText = `🛠️ ${bold('𝗔𝗗𝗠𝗜𝗡 𝗣𝗔𝗡𝗘𝗟')}\n\n` +
    `📊 ${bold('𝗦𝗧𝗔𝗧𝗦 𝗢𝗩𝗘𝗥𝗩𝗜𝗘𝗪')}:\n` +
    `👥 ${bold('𝗧𝗢𝗧𝗔𝗟 𝗨𝗦𝗘𝗥𝗦')}: ${bold(stats.totalUsers.toString())}\n` +
    `📦 ${bold('𝗧𝗢𝗧𝗔𝗟 𝗢𝗥𝗗𝗘𝗥𝗦')}: ${bold(stats.totalOrders.toString())}\n\n` +
    `🔧 ${bold('𝗠𝗔𝗡𝗔𝗚𝗘 𝗬𝗢𝗨𝗥 𝗕𝗢𝗧 𝗦𝗘𝗧𝗧𝗜𝗡𝗚𝗦 𝗛𝗘𝗥𝗘')}:`;

  safeSendMessage(chatId, msgText, {
    reply_markup: {
      inline_keyboard: [
        [{ text: `📊 ${bold('𝗦𝗘𝗧 𝗥𝗔𝗧𝗘')}`, callback_data: 'admin_set_rate' }, { text: `📡 ${bold('𝗕𝗥𝗢𝗔𝗗𝗖𝗔𝗦𝗧')}`, callback_data: 'admin_broadcast' }],
        [{ text: `➕ ${bold('𝗠𝗔𝗡𝗔𝗚𝗘 𝗗𝗘𝗣𝗢𝗦𝗜𝗧')}`, callback_data: 'admin_manage_dep' }, { text: `🏧 ${bold('𝗠𝗔𝗡𝗔𝗚𝗘 𝗪𝗜𝗧𝗛𝗗𝗥𝗔𝗪')}`, callback_data: 'admin_manage_with' }],
        [{ text: `👤 ${bold('𝗠𝗔𝗡𝗔𝗚𝗘 𝗔𝗗𝗠𝗜𝗡𝗦')}`, callback_data: 'admin_manage_admins' }, { text: `👥 ${bold('𝗦𝗘𝗧 𝗚𝗥𝗢𝗨𝗣')}`, callback_data: 'admin_set_group' }],
        [{ text: `🎧 ${bold('𝗦𝗘𝗧 𝗦𝗨𝗣𝗣𝗢𝗥𝗧')}`, callback_data: 'admin_set_support' }],
        [{ text: `🔙 ${bold('𝗖𝗟𝗢𝗦𝗘 𝗣𝗔𝗡𝗘𝗟')}`, callback_data: 'menu_main' }]
      ]
    }
  });
}

bot.on('callback_query', async (query) => {
  const chatId = query.message?.chat.id;
  const userId = query.from.id;
  if (!chatId) return;

  const data = query.data;

  // Navigation
  if (data === 'menu_main') {
    delete userStates[userId];
    safeSendMessage(chatId, `🏠 ${bold('𝗠𝗔𝗜𝗡 𝗠𝗘𝗡𝗨')}`, getMainMenu(userId));
    bot.answerCallbackQuery(query.id);
    return;
  }

  // Handle flow via callback
  if (data?.startsWith('deposit_')) {
    const methodName = data.split('_')[1];
    const method = settings.depositMethods.find(m => m.name === methodName);
    if (method && userStates[userId]) {
      userStates[userId].data.depositMethod = method;
      userStates[userId].step = 'ENTER_AMOUNT';
      safeEditMessage(chatId, query.message!.message_id, `💵 ${bold('𝗘𝗡𝗧𝗘𝗥 𝗔𝗠𝗢𝗨𝗡𝗧 (𝗨𝗦𝗗)')}\n\n💹 ${bold('𝗖𝗨𝗥𝗥𝗘𝗡𝗧 𝗥𝗔𝗧𝗘')}: ${bold('𝟭 𝗨𝗦𝗗 = ' + settings.exchangeRate + ' 𝗕𝗗𝗧')}\n\n👇 ${bold('𝗣𝗟𝗘𝗔𝗦𝗘 𝗘𝗡𝗧𝗘𝗥 𝗧𝗛𝗘 𝗧𝗢𝗧𝗔𝗟 𝗗𝗢𝗟𝗟𝗔𝗥𝗦 𝗬𝗢𝗨 𝗪𝗜𝗦𝗛 𝗧𝗢 𝗦𝗘𝗟𝗟')}:`, {
        reply_markup: { inline_keyboard: [[{ text: `🔙 ${bold('𝗕𝗔𝗖𝗞')}`, callback_data: 'menu_sell' }]] }
      });
    }
    bot.answerCallbackQuery(query.id);
    return;
  }

  if (data === 'menu_sell') {
    userStates[userId] = { step: 'SELECT_DEPOSIT_METHOD', data: {} };
    const methods = settings.depositMethods.map(m => [{ text: `💳 ${bold(m.name)}`, callback_data: `deposit_${m.name}` }]);
    safeEditMessage(chatId, query.message!.message_id, `🏦 ${bold('Choose How You Want To Pay')}\n\n👇 ${bold('Select where you will send your money')}:`, {
      reply_markup: { inline_keyboard: [...methods, [{ text: `🔙 ${bold('Back to Menu')}`, callback_data: 'menu_main' }]] }
    });
    bot.answerCallbackQuery(query.id);
    return;
  }

  if (data?.startsWith('withdraw_')) {
    const methodName = data.split('_')[1];
    if (userStates[userId]) {
      userStates[userId].data.withdrawalMethod = methodName;
      userStates[userId].step = 'ENTER_ACCOUNT_NUMBER';
      safeEditMessage(chatId, query.message!.message_id, `💳 ${bold('ENTER YOUR ' + methodName + ' NUMBER')}\n\n👇 ${bold('PLEASE PROVIDE THE ACCOUNT NUMBER WHERE WE WILL SEND YOUR MONEY')}:`, {
        reply_markup: { inline_keyboard: [[{ text: `🔙 ${bold('𝗕𝗔𝗖𝗞')}`, callback_data: 'none' }]] } // none because screenshot logic happened before
      });
    }
    bot.answerCallbackQuery(query.id);
    return;
  }

  // Admin Actions
  if (!isAdminUser(userId)) {
    bot.answerCallbackQuery(query.id, { text: '❌ ACCESS DENIED', show_alert: true });
    return;
  }

  if (data === 'admin_set_rate') {
    userStates[userId] = { step: 'ADMIN_SET_RATE', data: {} };
    safeEditMessage(chatId, query.message!.message_id, `📈 ${bold('𝗘𝗡𝗧𝗘𝗥 𝗡𝗘𝗪 𝗘𝗫𝗖𝗛𝗔𝗡𝗚𝗘 𝗥𝗔𝗧𝗘')}:`, {
      reply_markup: { inline_keyboard: [[{ text: `🔙 ${bold('𝗕𝗔𝗖𝗞')}`, callback_data: 'menu_admin' }]] }
    });
  } else if (data === 'admin_add_deposit') {
    userStates[userId] = { step: 'ADMIN_ADD_METHOD_NAME', data: {} };
    safeEditMessage(chatId, query.message!.message_id, `➕ ${bold('𝗘𝗡𝗧𝗘𝗥 𝗡𝗔𝗠𝗘 𝗙𝗢𝗥 𝗗𝗘𝗣𝗢𝗦𝗜𝗧 𝗠𝗘𝗧𝗛𝗢𝗗')}:`, {
      reply_markup: { inline_keyboard: [[{ text: `🔙 ${bold('𝗕𝗔𝗖𝗞')}`, callback_data: 'admin_manage_dep' }]] }
    });
  } else if (data === 'admin_add_withdraw') {
    userStates[userId] = { step: 'ADMIN_ADD_WITHDRAW_NAME', data: {} };
    safeEditMessage(chatId, query.message!.message_id, `🏧 ${bold('𝗘𝗡𝗧𝗘𝗥 𝗡𝗔𝗠𝗘 𝗙𝗢𝗥 𝗪𝗜𝗧𝗛𝗗𝗥𝗔𝗪𝗔𝗟 𝗠𝗘𝗧𝗛𝗢𝗗')}:`, {
      reply_markup: { inline_keyboard: [[{ text: `🔙 ${bold('𝗕𝗔𝗖𝗞')}`, callback_data: 'admin_manage_with' }]] }
    });
  } else if (data === 'admin_add_new') {
    userStates[userId] = { step: 'ADMIN_ADD_USER', data: {} };
    safeEditMessage(chatId, query.message!.message_id, `👤 ${bold('𝗘𝗡𝗧𝗘𝗥 𝗧𝗘𝗟𝗘𝗚𝗥𝗔𝗠 𝗨𝗦𝗘𝗥 𝗜𝗗 𝗧𝗢 𝗔𝗗𝗗 𝗔𝗦 𝗔𝗗𝗠𝗜𝗡')}:`, {
      reply_markup: { inline_keyboard: [[{ text: `🔙 ${bold('𝗕𝗔𝗖𝗞')}`, callback_data: 'admin_manage_admins' }]] }
    });
  } else if (data === 'admin_set_support') {
    const buttons = [
      [{ text: `🔄 ${bold('𝗖𝗛𝗔𝗡𝗚𝗘 𝗨𝗦𝗘𝗥𝗡𝗔𝗠𝗘')}`, callback_data: 'admin_input_support' }],
      [{ text: `🔙 ${bold('𝗕𝗔𝗖𝗞')}`, callback_data: 'menu_admin' }]
    ];
    safeEditMessage(chatId, query.message!.message_id, `🎧 ${bold('𝗠𝗔𝗡𝗔𝗚𝗘 𝗦𝗨𝗣𝗣𝗢𝗥𝗧 𝗔𝗖𝗖𝗢𝗨𝗡𝗧')}\n\n${bold('𝗖𝗨𝗥𝗥𝗘𝗡𝗧')}: @${settings.supportUsername}`, {
      reply_markup: { inline_keyboard: buttons }
    });
  } else if (data === 'admin_input_support') {
    userStates[userId] = { step: 'ADMIN_SET_SUPPORT', data: {} };
    safeEditMessage(chatId, query.message!.message_id, `🎧 ${bold('𝗘𝗡𝗧𝗘𝗥 𝗡𝗘𝗪 𝗦𝗨𝗣𝗣𝗢𝗥𝗧 𝗨𝗦𝗘𝗥𝗡𝗔𝗠𝗘 (𝗪𝗜𝗧𝗛𝗢𝗨𝗧 @)')}:`, {
      reply_markup: { inline_keyboard: [[{ text: `🔙 ${bold('𝗕𝗔𝗖𝗞')}`, callback_data: 'admin_set_support' }]] }
    });
  } else if (data === 'admin_broadcast') {
    userStates[userId] = { step: 'ADMIN_BROADCAST', data: {} };
    safeEditMessage(chatId, query.message!.message_id, `📡 ${bold('𝗕𝗥𝗢𝗔𝗗𝗖𝗔𝗦𝗧 𝗙𝗘𝗔𝗧𝗨𝗥𝗘')}\n\n✍️ ${bold('𝗘𝗡𝗧𝗘𝗥 𝗧𝗛𝗘 𝗠𝗘𝗦𝗦𝗔𝗚𝗘 𝗬𝗢𝗨 𝗪𝗔𝗡𝗧 𝗧𝗢 𝗦𝗘𝗡𝗗 𝗧𝗢 𝗔𝗟𝗟 𝗨𝗦𝗘𝗥𝗦')}:`, {
      reply_markup: { inline_keyboard: [[{ text: `🔙 ${bold('𝗖𝗔𝗡𝗖𝗘𝗟')}`, callback_data: 'menu_admin' }]] }
    });
  } else if (data === 'menu_admin') {
    showAdminPanel(chatId);
  } else if (data === 'admin_manage_dep') {
    const buttons = settings.depositMethods.map(m => [{ text: `❌ ${bold('𝗗𝗘𝗟𝗘𝗧𝗘')} ${m.name}`, callback_data: `delete_dep_${m.name}` }]);
    buttons.push([{ text: `➕ ${bold('𝗔𝗗𝗗 𝗡𝗘𝗪 𝗠𝗘𝗧𝗛𝗢𝗗')}`, callback_data: 'admin_add_deposit' }]);
    buttons.push([{ text: `🔙 ${bold('𝗕𝗔𝗖𝗞')}`, callback_data: 'menu_admin' }]);
    safeEditMessage(chatId, query.message!.message_id, `💳 ${bold('𝗠𝗔𝗡𝗔𝗚𝗘 𝗗𝗘𝗣𝗢𝗦𝗜𝗧 𝗠𝗘𝗧𝗛𝗢𝗗𝗦')}:`, {
      reply_markup: { inline_keyboard: buttons }
    });
  } else if (data === 'admin_manage_with') {
    const buttons = settings.withdrawalMethods.map(m => [{ text: `❌ ${bold('𝗗𝗘𝗟𝗘𝗧𝗘')} ${m}`, callback_data: `delete_with_${m}` }]);
    buttons.push([{ text: `➕ ${bold('𝗔𝗗𝗗 𝗡𝗘𝗪 𝗠𝗘𝗧𝗛𝗢𝗗')}`, callback_data: 'admin_add_withdraw' }]);
    buttons.push([{ text: `🔙 ${bold('𝗕𝗔𝗖𝗞')}`, callback_data: 'menu_admin' }]);
    safeEditMessage(chatId, query.message!.message_id, `🏧 ${bold('𝗠𝗔𝗡𝗔𝗚𝗘 𝗪𝗜𝗧𝗛𝗗𝗥𝗔𝗪𝗔𝗟 𝗠𝗘𝗧𝗛𝗢𝗗𝗦')}:`, {
      reply_markup: { inline_keyboard: buttons }
    });
  } else if (data === 'admin_manage_admins') {
    const removableAdmins = settings.admins.filter(id => !PERMANENT_ADMIN_IDS.includes(id));
    const buttons = removableAdmins.map(id => [{ text: `❌ ${bold('𝗥𝗘𝗠𝗢𝗩𝗘')} ${id}`, callback_data: `delete_admin_${id}` }]);
    buttons.push([{ text: `➕ ${bold('𝗔𝗗𝗗 𝗡𝗘𝗪 𝗔𝗗𝗠𝗜𝗡')}`, callback_data: 'admin_add_new' }]);
    buttons.push([{ text: `🔙 ${bold('𝗕𝗔𝗖𝗞')}`, callback_data: 'menu_admin' }]);
    safeEditMessage(chatId, query.message!.message_id, `👤 ${bold('𝗠𝗔𝗡𝗔𝗚𝗘 𝗔𝗗𝗠𝗜𝗡𝗜𝗦𝗧𝗥𝗔𝗧𝗢𝗥𝗦')}:`, {
      reply_markup: { inline_keyboard: buttons }
    });
  } else if (data === 'admin_set_group') {
    const buttons = [
      [{ text: `🔄 ${bold('𝗖𝗛𝗔𝗡𝗚𝗘 𝗚𝗥𝗢𝗨𝗣 𝗜𝗗')}`, callback_data: 'admin_input_group' }],
      [{ text: `🗑️ ${bold('𝗗𝗘𝗟𝗘𝗧𝗘 𝗚𝗥𝗢𝗨𝗣')}`, callback_data: 'admin_delete_group' }],
      [{ text: `🔙 ${bold('𝗕𝗔𝗖𝗞')}`, callback_data: 'menu_admin' }]
    ];
    safeEditMessage(chatId, query.message!.message_id, `👥 ${bold('𝗠𝗔𝗡𝗔𝗚𝗘 𝗔𝗗𝗠𝗜𝗡 𝗚𝗥𝗢𝗨𝗣')}\n\n${bold('𝗖𝗨𝗥𝗥𝗘𝗡𝗧 𝗜𝗗')}: ${settings.adminGroupId || 'None'}`, {
      reply_markup: { inline_keyboard: buttons }
    });
  } else if (data === 'admin_input_group') {
    userStates[userId] = { step: 'ADMIN_SET_GROUP', data: {} };
    safeEditMessage(chatId, query.message!.message_id, `👥 ${bold('𝗘𝗡𝗧𝗘𝗥 𝗡𝗘𝗪 𝗔𝗗𝗠𝗜𝗡 𝗚𝗥𝗢𝗨𝗣 𝗜𝗗 (𝗲.𝗴. -𝟭𝟬𝟬𝟭𝟮𝟯𝟰𝟱𝟲𝟳𝟴𝟵)')}:`, {
      reply_markup: { inline_keyboard: [[{ text: `🔙 ${bold('𝗕𝗔𝗖𝗞')}`, callback_data: 'admin_set_group' }]] }
    });
  } else if (data === 'admin_delete_group') {
    settings.adminGroupId = null;
    await saveSettings();
    bot.answerCallbackQuery(query.id, { text: 'Group ID Deleted', show_alert: true });
    showAdminPanel(chatId);
  } else if (data?.startsWith('delete_dep_')) {
    const name = data.replace('delete_dep_', '');
    settings.depositMethods = settings.depositMethods.filter(m => m.name !== name);
    await saveSettings();
    bot.answerCallbackQuery(query.id, { text: 'Deleted' });
    const buttons = settings.depositMethods.map(m => [{ text: `❌ ${bold('𝗗𝗘𝗟𝗘𝗧𝗘')} ${m.name}`, callback_data: `delete_dep_${m.name}` }]);
    buttons.push([{ text: `➕ ${bold('𝗔𝗗𝗗 𝗡𝗘𝗪 𝗠𝗘𝗧𝗛𝗢𝗗')}`, callback_data: 'admin_add_deposit' }]);
    buttons.push([{ text: `🔙 ${bold('𝗕𝗔𝗖𝗞')}`, callback_data: 'menu_admin' }]);
    safeEditMessage(chatId, query.message!.message_id, `💳 ${bold('𝗠𝗔𝗡𝗔𝗚𝗘 𝗗𝗘𝗣𝗢𝗦𝗜𝗧 𝗠𝗘𝗧𝗛𝗢𝗗𝗦')}:`, {
      reply_markup: { inline_keyboard: buttons }
    });
  } else if (data?.startsWith('delete_with_')) {
    const name = data.replace('delete_with_', '');
    settings.withdrawalMethods = settings.withdrawalMethods.filter(m => m !== name);
    await saveSettings();
    bot.answerCallbackQuery(query.id, { text: 'Deleted' });
    const buttons = settings.withdrawalMethods.map(m => [{ text: `❌ ${bold('𝗗𝗘𝗟𝗘𝗧𝗘')} ${m}`, callback_data: `delete_with_${m}` }]);
    buttons.push([{ text: `➕ ${bold('𝗔𝗗𝗗 𝗡𝗘𝗪 𝗠𝗘𝗧𝗛𝗢𝗗')}`, callback_data: 'admin_add_withdraw' }]);
    buttons.push([{ text: `🔙 ${bold('𝗕𝗔𝗖𝗞')}`, callback_data: 'menu_admin' }]);
    safeEditMessage(chatId, query.message!.message_id, `🏧 ${bold('𝗠𝗔𝗡𝗔𝗚𝗘 𝗪𝗜𝗧𝗛𝗗𝗥𝗔𝗪𝗔𝗟 𝗠𝗘𝗧𝗛𝗢𝗗𝗦')}:`, {
      reply_markup: { inline_keyboard: buttons }
    });
  } else if (data?.startsWith('delete_admin_')) {
    const id = parseInt(data.replace('delete_admin_', ''));
    settings.admins = settings.admins.filter(a => a !== id);
    await saveSettings();
    bot.answerCallbackQuery(query.id, { text: 'Deleted' });
    const removableAdmins = settings.admins.filter(adminId => !PERMANENT_ADMIN_IDS.includes(adminId));
    const buttons = removableAdmins.map(adminId => [{ text: `❌ ${bold('𝗥𝗘𝗠𝗢𝗩𝗘')} ${adminId}`, callback_data: `delete_admin_${adminId}` }]);
    buttons.push([{ text: `➕ ${bold('𝗔𝗗𝗗 𝗡𝗘𝗪 𝗔𝗗𝗠𝗜𝗡')}`, callback_data: 'admin_add_new' }]);
    buttons.push([{ text: `🔙 ${bold('𝗕𝗔𝗖𝗞')}`, callback_data: 'menu_admin' }]);
    safeEditMessage(chatId, query.message!.message_id, `👤 ${bold('𝗠𝗔𝗡𝗔𝗚𝗘 𝗔𝗗𝗠𝗜𝗡𝗜𝗦𝗧𝗥𝗔𝗧𝗢𝗥𝗦')}:`, {
      reply_markup: { inline_keyboard: buttons }
    });
  } else if (data?.startsWith('approve_')) {
    const targetUserId = parseInt(data.split('_')[1]);
    bot.sendMessage(targetUserId, `✅ ${bold('𝗣𝗔𝗬𝗠𝗘𝗡𝗧 𝗦𝗨𝗖𝗖𝗘𝗦𝗦𝗙𝗨𝗟')}\n\n💸 ${bold('𝗥𝗘𝗤𝗨𝗘𝗦𝗧𝗘𝗗 𝗙𝗨𝗡𝗗𝗦 𝗛𝗔𝗩𝗘 𝗕𝗘𝗘𝗡 𝗦𝗨𝗖𝗖𝗘𝗦𝗦𝗙𝗨𝗟𝗟𝗬 𝗦𝗘𝗡𝗧 𝗧𝗢 𝗬𝗢𝗨𝗥 𝗣𝗥𝗢𝗩𝗜𝗗𝗘𝗗 𝗡𝗨𝗠𝗕𝗘𝗥.')}`);
    bot.editMessageReplyMarkup({
      inline_keyboard: [[{ text: `✅ ${bold('𝗔𝗣𝗣𝗥𝗢𝗩𝗘𝗗')}`, callback_data: 'none' }]]
    }, { chat_id: chatId, message_id: query.message?.message_id });
  } else if (data?.startsWith('reject_')) {
    const targetUserId = parseInt(data.split('_')[1]);
    bot.sendMessage(targetUserId, `❌ ${bold('𝗥𝗘𝗤𝗨𝗘𝗦𝗧 𝗥𝗘𝗝𝗘𝗖𝗧𝗘𝗗')}\n\n📨 ${bold('𝗬𝗢𝗨𝗥 𝗧𝗥𝗔𝗗𝗘 𝗥𝗘𝗤𝗨𝗘𝗦𝗧 𝗛𝗔𝗦 𝗕𝗘𝗘𝗡 𝗥𝗘𝗝𝗘𝗖𝗧𝗘𝗗 𝗕𝗬 𝗧𝗛𝗘 𝗔𝗗𝗠𝗜𝗡𝗜𝗦𝗧𝗥𝗔𝗧𝗢𝗥. 𝗖𝗢𝗡𝗧𝗔𝗖𝗧 𝗦𝗨𝗣𝗣𝗢𝗥𝗧 𝗙𝗢𝗥 𝗖𝗟𝗔𝗥𝗜𝗙𝗜𝗖𝗔𝗧𝗜𝗢𝗡.')}`);
    bot.editMessageReplyMarkup({
      inline_keyboard: [[{ text: `❌ ${bold('𝗥𝗘𝗝𝗘𝗖𝗧𝗘𝗗')}`, callback_data: 'none' }]]
    }, { chat_id: chatId, message_id: query.message?.message_id });
  }
  bot.answerCallbackQuery(query.id);
});

function submitRequest(chatId: number, userId: number, data: any, firstName: string) {
  if (!settings.adminGroupId) {
    bot.sendMessage(chatId, `⚠️ ${bold('𝗘𝗥𝗥𝗢𝗥: 𝗔𝗗𝗠𝗜𝗡 𝗚𝗥𝗢𝗨𝗣 𝗡𝗢𝗧 𝗦𝗘𝗧. 𝗣𝗟𝗘𝗔𝗦𝗘 𝗖𝗢𝗡𝗧𝗔𝗖𝗧 𝗔𝗗𝗠𝗜𝗡.')}`);
    return;
  }

  const userLink = `[${firstName}](tg://user?id=${userId})`;
  const message = `${bold('𝗨𝗦𝗘𝗥')}: ${userLink}\n\n` +
    `${bold('𝗗𝗘𝗣𝗢𝗦𝗜𝗧 𝗔𝗠𝗢𝗨𝗡𝗧')}: ${data.amount} USD\n\n` +
    `${bold('𝗧𝗥𝗔𝗡𝗦𝗔𝗖𝗧𝗜𝗢𝗡 𝗜𝗗')}: ${data.txId}\n\n` +
    `${bold('𝗗𝗘𝗣𝗢𝗦𝗜𝗧 𝗠𝗘𝗧𝗛𝗢𝗗')}: ${data.depositMethod.name}\n\n` +
    `${bold('𝗪𝗜𝗧𝗛𝗗𝗥𝗔𝗪𝗔𝗟 𝗔𝗠𝗢𝗨𝗡𝗧')}: ${data.totalBdt} BDT\n\n` +
    `${bold('𝗪𝗜𝗧𝗛𝗗𝗥𝗔𝗪𝗔𝗟 𝗡𝗨𝗠𝗕𝗘𝗥')}: \`${data.accountNumber}\`\n\n` +
    `${bold('𝗪𝗜𝗧𝗛𝗗𝗥𝗔𝗪𝗔𝗟 𝗠𝗘𝗧𝗛𝗢𝗗')}: ${data.withdrawalMethod}`;

  const keyboard = {
    reply_markup: {
      inline_keyboard: [
        [
          { text: `✅ ${bold('𝗔𝗣𝗣𝗥𝗢𝗩𝗘')}`, callback_data: `approve_${userId}` },
          { text: `❌ ${bold('𝗥𝗘𝗝𝗘𝗖𝗧')}`, callback_data: `reject_${userId}` }
        ]
      ]
    }
  };

  if (data.screenshotId) {
    bot.sendPhoto(settings.adminGroupId, data.screenshotId, {
      caption: message,
      parse_mode: 'Markdown',
      ...keyboard
    });
  } else {
    bot.sendMessage(settings.adminGroupId, message, {
      parse_mode: 'Markdown',
      ...keyboard
    });
  }
}

// Vite Server Integration
async function startServer() {
  const app = express();
  const PORT = 3000;

  await loadSettings();

  if (process.env.NODE_ENV !== 'production') {
    const vite = await createViteServer({
      server: { middlewareMode: true },
      appType: 'spa',
    });
    app.use(vite.middlewares);
  } else {
    const distPath = path.join(process.cwd(), 'dist');
    app.use(express.static(distPath));
    app.get('*', (req, res) => {
      res.sendFile(path.join(distPath, 'index.html'));
    });
  }

  app.listen(PORT, '0.0.0.0', () => {
    console.log(`Server running on http://localhost:${PORT}`);
    console.log('Telegram Bot is active with Firebase.');
  });
}

startServer();
