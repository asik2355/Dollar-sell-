/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import { motion } from "motion/react";
import { MessageSquare, ShieldCheck, Activity, Settings } from "lucide-react";

export default function App() {
  return (
    <div className="min-h-screen bg-slate-950 text-white font-sans selection:bg-indigo-500/30">
      <div className="max-w-4xl mx-auto px-6 py-20">
        <motion.div 
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="space-y-6 text-center"
        >
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 text-sm font-medium">
            <Activity className="w-4 h-4 animate-pulse" />
            Bot Service 2.0 (Firebase Active)
          </div>
          
          <h1 className="text-5xl md:text-7xl font-bold tracking-tight text-white uppercase italic leading-tight">
            𝗗𝗼𝗹𝗹𝗮𝗿 <span className="text-indigo-500">𝗘𝘅𝗰𝗵𝗮𝗻𝗴𝗲</span><br/>
            <span className="text-3xl md:text-5xl text-slate-500">𝗣𝗿𝗼𝗳𝗲𝘀𝘀𝗶𝗼𝗻𝗮𝗹 𝗕𝗼𝘁</span>
          </h1>

          <p className="text-slate-400 text-lg max-w-2xl mx-auto leading-relaxed">
            Cloud-synced dollar trading bot powered by Google Firebase. Features real-time broadcast, request verification, and instant admin controls.
          </p>

          <div className="grid grid-cols-1 md:grid-cols-4 gap-6 mt-16 text-left text-sm uppercase tracking-widest font-bold">
            <div className="p-8 rounded-2xl bg-white/5 border border-white/10 hover:border-white/20 transition-all group">
              <MessageSquare className="w-8 h-8 text-indigo-500 mb-6 group-hover:scale-110 transition-transform" />
              <h3 className="mb-2">Sell Flow</h3>
              <p className="text-slate-500 normal-case font-normal leading-relaxed">Secure USD to BDT flows with multi-method support.</p>
            </div>
            
            <div className="p-8 rounded-2xl bg-white/5 border border-white/10 hover:border-white/20 transition-all group">
              <ShieldCheck className="w-8 h-8 text-indigo-500 mb-6 group-hover:scale-110 transition-transform" />
              <h3 className="mb-2">Firebase DB</h3>
              <p className="text-slate-500 normal-case font-normal leading-relaxed">All settings, users, and logs are synced to the cloud.</p>
            </div>
            
            <div className="p-8 rounded-2xl bg-white/5 border border-white/10 hover:border-white/20 transition-all group">
              <Activity className="w-8 h-8 text-indigo-500 mb-6 group-hover:scale-110 transition-transform" />
              <h3 className="mb-2">Broadcast</h3>
              <p className="text-slate-500 normal-case font-normal leading-relaxed">Send mass notifications to your entire user base instantly.</p>
            </div>

            <div className="p-8 rounded-2xl bg-white/5 border border-white/10 hover:border-white/20 transition-all group shadow-2xl shadow-indigo-500/10">
              <Settings className="w-8 h-8 text-indigo-500 mb-6 group-hover:scale-110 transition-transform" />
              <h3 className="mb-2">Back Nav</h3>
              <p className="text-slate-500 normal-case font-normal leading-relaxed">Smooth navigation with back buttons in every step.</p>
            </div>
          </div>

          <div className="mt-20 pt-10 border-t border-white/5 text-slate-500 flex flex-col md:flex-row justify-between items-center gap-4 text-xs font-mono uppercase tracking-widest">
            <span>Server Running on Port 3000</span>
            <span>Bot: @your_bot_id (8716745260)</span>
            <span className="text-indigo-400">Status: Listening for updates...</span>
          </div>
        </motion.div>
      </div>
    </div>
  );
}

