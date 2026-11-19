<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'

type Analysis = {
  asset: string
  synthesis: string
  quantum: { current_price: number; expected_price: number; expected_return: number; confidence: number; forecast: { date: string; expected: number; lower: number; upper: number }[] }
  sentiment: { score: number; correlation: number; headlines: { headline: string; score: number }[] }
  extreme_events: { risk_probability: number; regime: string; anomaly: boolean; features: Record<string, number> }
}

const asset = ref('AAPL')
const horizon = ref(10)
const timeframe = ref('1d')
const loading = ref(false)
const analysis = ref<Analysis | null>(null)
const health = ref<any>({ local_llm: { online: false } })
const chat = ref('')
const messages = ref<{ role: string; text: string }[]>([])
const chartPoints = computed(() => analysis.value?.quantum.forecast ?? [])

async function runAnalysis() {
  loading.value = true
  try {
    const response = await fetch('http://127.0.0.1:8000/api/analyze', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ asset: asset.value, horizon: horizon.value, timeframe: timeframe.value })
    })
    analysis.value = await response.json()
  } finally { loading.value = false }
}

async function sendMessage() {
  if (!chat.value.trim()) return
  const prompt = chat.value
  messages.value.push({ role: 'user', text: prompt })
  chat.value = ''
  const response = await fetch('http://127.0.0.1:8000/api/agent/stream', {
    method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ message: prompt, asset: asset.value, horizon: horizon.value, session_id: 'dashboard' })
  })
  const reader = response.body?.getReader()
  const decoder = new TextDecoder()
  let text = ''
  if (reader) {
    while (true) {
      const { done, value } = await reader.read()
      if (done) break
      text += decoder.decode(value)
    }
  }
  messages.value.push({ role: 'assistant', text })
}

onMounted(async () => {
  const response = await fetch('http://127.0.0.1:8000/api/health')
  health.value = await response.json()
  runAnalysis()
})
</script>

<template>
  <main class="shell">
    <header class="topbar">
      <div>
        <p class="eyebrow">MARKET PREDICTOR PRICE</p>
        <h1>Quant workstation</h1>
      </div>
      <div class="controls">
        <label>Asset <input v-model="asset" @keyup.enter="runAnalysis" /></label>
        <label>Timeframe <select v-model="timeframe"><option>1d</option><option>1h</option></select></label>
        <label>Horizon <input v-model.number="horizon" type="number" min="1" max="90" /></label>
        <button class="primary" :disabled="loading" @click="runAnalysis">{{ loading ? 'Running…' : 'Run analysis' }}</button>
      </div>
    </header>

    <section class="status-row">
      <span class="pill live">● Pipeline ready</span>
      <span class="pill">Quantum engine ready</span>
      <span class="pill">ML risk ready</span>
      <span class="pill" :class="{ warn: !health.local_llm?.online }">Local LLM {{ health.local_llm?.online ? 'online' : 'offline' }}</span>
    </section>

    <section v-if="analysis" class="dashboard">
      <div class="hero card">
        <div class="card-title"><span>Forecast path</span><strong>{{ analysis.asset }}</strong></div>
        <div class="chart">
          <svg viewBox="0 0 760 240" preserveAspectRatio="none">
            <polyline :points="chartPoints.map((p, i) => `${i * (740 / Math.max(chartPoints.length - 1, 1)) + 10},${220 - ((p.expected - Math.min(...chartPoints.map(x => x.lower))) / Math.max(Math.max(...chartPoints.map(x => x.upper)) - Math.min(...chartPoints.map(x => x.lower)), 1)) * 190}`).join(' ')" fill="none" stroke="#77e6c1" stroke-width="3" />
          </svg>
        </div>
        <div class="legend"><span>Expected path</span><span>10–90% uncertainty envelope</span></div>
        <p class="synthesis">{{ analysis.synthesis }}</p>
      </div>
      <aside class="card agent">
        <div class="card-title"><span>Local AI copilot</span><span class="dot"></span></div>
        <div class="messages"><p v-if="!messages.length" class="muted">Ask for a synthesis, sentiment read, risk scan, or forecast.</p><p v-for="(message, i) in messages" :key="i" :class="message.role">{{ message.text }}</p></div>
        <form @submit.prevent="sendMessage"><input v-model="chat" placeholder="Explain the current chart…" /><button>Send</button></form>
      </aside>
      <div class="metrics">
        <article class="card metric"><span class="label">Quantum forecast</span><strong>{{ analysis.quantum.expected_price.toFixed(2) }}</strong><small>{{ (analysis.quantum.expected_return * 100).toFixed(2) }}% expected return · {{ (analysis.quantum.confidence * 100).toFixed(0) }}% confidence</small></article>
        <article class="card metric"><span class="label">News sentiment</span><strong>{{ analysis.sentiment.score.toFixed(2) }}</strong><small>Correlation {{ analysis.sentiment.correlation.toFixed(2) }} · {{ analysis.sentiment.headlines.length }} signals</small></article>
        <article class="card metric risk"><span class="label">Tail-risk probability</span><strong>{{ (analysis.extreme_events.risk_probability * 100).toFixed(1) }}%</strong><small>{{ analysis.extreme_events.regime }} regime · {{ analysis.extreme_events.anomaly ? 'Anomaly detected' : 'No anomaly' }}</small></article>
      </div>
    </section>
  </main>
</template>
